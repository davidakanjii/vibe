"""Deterministic server-side PCM DSP; transport/SFU adapter intentionally separate.

48 kHz, stereo, signed little-endian PCM16, 480 frames (10 ms) per block.
Grant configuration is trusted server state, never client supplied. Priority is
assigned in the grant. Highest-priority active voice(s) win per destination.
"""
from dataclasses import dataclass
from math import isfinite
from struct import unpack, pack
from typing import Mapping

RATE=48000
CHANNELS=2
FRAMES=480
SAMPLES=FRAMES*CHANNELS
BLOCK_BYTES=SAMPLES*2
SILENCE=bytes(BLOCK_BYTES)

@dataclass(frozen=True)
class RouteGrant:
    speaker_id:str
    event_id:str
    zone:str
    channel_ids:frozenset[str]
    broadcast_all:bool=False
    priority:int=0

@dataclass(frozen=True)
class VoiceBlock:
    speaker_id:str
    pcm:bytes
    channel_ids:frozenset[str]
    active:bool=True
    muted:bool=False
    push_to_talk:bool=False
    pressed:bool=False
    gain:float=1.0
    broadcast_all:bool=False

class RoutingDenied(ValueError): pass

class AudioMixer:
    def __init__(self,event_id:str,channel_zones:Mapping[str,str],grants:tuple[RouteGrant,...],duck_gain:float=0.25):
        if not isfinite(duck_gain) or not 0<=duck_gain<=1: raise ValueError('Invalid duck gain')
        self.event_id=event_id
        self.channel_zones=dict(channel_zones)
        self.grants={g.speaker_id:g for g in grants}
        if len(self.grants)!=len(grants): raise ValueError('Duplicate speaker grant')
        self.duck_gain=duck_gain
        for grant in grants:
            if grant.event_id!=event_id: raise RoutingDenied('Grant belongs to another event')
            if not grant.channel_ids or any(self.channel_zones.get(c)!=grant.zone for c in grant.channel_ids): raise RoutingDenied('Grant crosses channel or zone boundary')
    @staticmethod
    def decode(pcm:bytes):
        if len(pcm)!=BLOCK_BYTES: raise ValueError(f'PCM block must contain {BLOCK_BYTES} bytes')
        return unpack('<'+'h'*SAMPLES,pcm)
    def mix(self,music:Mapping[str,bytes],voices:tuple[VoiceBlock,...],*,event_id:str,zone:str)->dict[str,bytes]:
        if event_id!=self.event_id: raise RoutingDenied('Event boundary violation')
        if any(self.channel_zones.get(c)!=zone for c in music): raise RoutingDenied('Music channel outside permitted zone')
        decoded={c:self.decode(pcm) for c,pcm in music.items()}
        routes={c:[] for c in music}
        seen=set()
        for voice in voices:
            if voice.speaker_id in seen: raise RoutingDenied('Duplicate speaker block')
            seen.add(voice.speaker_id)
            grant=self.grants.get(voice.speaker_id)
            if not grant or grant.event_id!=event_id or grant.zone!=zone: raise RoutingDenied('Speaker outside event or zone')
            if not isfinite(voice.gain) or not 0<=voice.gain<=4: raise ValueError('Gain must be between zero and four')
            if voice.broadcast_all and not grant.broadcast_all: raise RoutingDenied('Broadcast-all not authorised')
            if not voice.channel_ids<=grant.channel_ids: raise RoutingDenied('Unassigned channel')
            targets={c for c,z in self.channel_zones.items() if z==zone} if voice.broadcast_all else voice.channel_ids
            samples=self.decode(voice.pcm)
            if voice.muted or not voice.active or (voice.push_to_talk and not voice.pressed): continue
            for channel in targets:
                if channel in routes: routes[channel].append((grant.priority,voice.gain,samples))
        result={}
        for channel,samples in decoded.items():
            available=routes[channel]
            highest=max((item[0] for item in available),default=None)
            selected=[item for item in available if item[0]==highest]
            duck=self.duck_gain if selected else 1.0
            output=[]
            for index,sample in enumerate(samples):
                value=sample*duck+sum(gain*pcm[index] for _,gain,pcm in selected)
                output.append(max(-32768,min(32767,round(value))))
            result[channel]=pack('<'+'h'*SAMPLES,*output)
        return result
