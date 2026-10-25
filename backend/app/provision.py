"""Operator-only audited provisioning, outside unauthenticated application requests.
Run with production operator database credentials via protected deployment access.
"""
import argparse
from datetime import datetime
from .config import SessionLocal
from .models import Organisation, Licence, Audit

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('organisation_id'); parser.add_argument('--expires-at',required=True); parser.add_argument('--channels',type=int,default=4); parser.add_argument('--listeners',type=int,default=100); parser.add_argument('--operator',required=True); args=parser.parse_args()
    expires=datetime.fromisoformat(args.expires_at)
    if expires.tzinfo is None or not 1<=args.channels<=32 or not 1<=args.listeners<=100000: parser.error('Timezone and valid capacity limits required')
    with SessionLocal() as db:
        if not db.get(Organisation,args.organisation_id): parser.error('Unknown organisation')
        row=db.get(Licence,args.organisation_id)
        if not row: row=Licence(organisation_id=args.organisation_id); db.add(row)
        row.expires_at=expires; row.max_channels=args.channels; row.max_listeners=args.listeners
        db.add(Audit(action='operator.licence.grant',resource_id=args.organisation_id,actor_id=args.operator)); db.commit()
if __name__=='__main__': main()
