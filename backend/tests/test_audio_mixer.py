import pytest
from struct import pack,unpack
from app.audio_mixer import AudioMixer,RouteGrant,VoiceBlock,RoutingDenied,SAMPLES,SILENCE

def pcm(value): return pack('<'+'h'*SAMPLES,*([value]*SAMPLES))
def first(block): return unpack('<h',block[:2])[0]
def mixer(priority=0,broadcast=False): return AudioMixer('event',{'a':'main','b':'main','vip':'vip'},(RouteGrant('host','event','main',frozenset({'a'}),broadcast,priority),))
def test_duck_and_gain_are_applied_only_to_routed_channel():
    result=mixer().mix({'a':pcm(10000),'b':pcm(10000)},(VoiceBlock('host',pcm(2000),frozenset({'a'}),gain=2),),event_id='event',zone='main')
    assert first(result['a'])==6500
    assert first(result['b'])==10000

def test_clipping_saturates_both_directions():
    for value,expected in [(20000,32767),(-20000,-32768)]:
        result=mixer().mix({'a':pcm(value)},(VoiceBlock('host',pcm(value),frozenset({'a'}),gain=4),),event_id='event',zone='main')
        assert first(result['a'])==expected

def test_priority_and_push_to_talk_and_mute():
    engine=AudioMixer('event',{'a':'main'},(RouteGrant('host','event','main',frozenset({'a'}),priority=1),RouteGrant('emergency','event','main',frozenset({'a'}),priority=10)))
    result=engine.mix({'a':pcm(4000)},(VoiceBlock('host',pcm(1000),frozenset({'a'})),VoiceBlock('emergency',pcm(3000),frozenset({'a'}))),event_id='event',zone='main')
    assert first(result['a'])==4000
    for args in [{'muted':True},{'active':False},{'push_to_talk':True,'pressed':False}]:
        result=mixer().mix({'a':pcm(4000)},(VoiceBlock('host',pcm(3000),frozenset({'a'}),**args),),event_id='event',zone='main')
        assert first(result['a'])==4000

def test_unassigned_routes_broadcast_and_event_zone_are_rejected():
    engine=mixer()
    for voice in [VoiceBlock('host',SILENCE,frozenset({'b'})),VoiceBlock('host',SILENCE,frozenset({'a'}),broadcast_all=True),VoiceBlock('unknown',SILENCE,frozenset({'a'}))]:
        with pytest.raises(RoutingDenied): engine.mix({'a':SILENCE},(voice,),event_id='event',zone='main')
    with pytest.raises(RoutingDenied): engine.mix({'a':SILENCE},(),event_id='other',zone='main')
    with pytest.raises(RoutingDenied): engine.mix({'vip':SILENCE},(),event_id='event',zone='main')
    with pytest.raises(RoutingDenied): engine.mix({'vip':SILENCE},(VoiceBlock('host',SILENCE,frozenset({'a'})),),event_id='event',zone='vip')

def test_authorised_broadcast_stays_inside_zone_and_invalid_pcm_rejected():
    result=mixer(broadcast=True).mix({'a':SILENCE,'b':SILENCE},(VoiceBlock('host',pcm(1000),frozenset(),broadcast_all=True),),event_id='event',zone='main')
    assert first(result['a'])==first(result['b'])==1000
    with pytest.raises(ValueError): mixer().mix({'a':b'bad'},(),event_id='event',zone='main')
    with pytest.raises(ValueError): mixer().mix({'a':SILENCE},(VoiceBlock('host',SILENCE,frozenset({'a'}),gain=float('nan')),),event_id='event',zone='main')
