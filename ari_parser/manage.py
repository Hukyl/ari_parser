import argparse

import bot
import crawler
from models.db import AccountDatabase
from models import exceptions


parser = argparse.ArgumentParser(description='Manage the parser commands')
subparsers = parser.add_subparsers(help="command", dest='command')
parser_run = subparsers.add_parser('run', help='run the parser')
parser_run.add_argument(
    '-b', '--bot-only', help='To start the bot only', 
    default=False, action=argparse.BooleanOptionalAction
)
parser_db = subparsers.add_parser(
    'remove-appointment', 
    help='remove appointments from DB (-e and -n are mutually exclusive)'
)
parser_db.add_argument(
    '-e', '--email', action='append', default=list(), dest='emails',
    help='email of main applicant', required=False
)
parser_db.add_argument(
    '-n', '--name', action='append', default=list(), dest='names',
    help='name of the dependent applicant', required=False
)


if __name__ == '__main__':
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
    elif args.command == 'run':
        if args.bot_only:
            bot.main()
        else:
            crawler.main()
    elif args.command == 'remove-appointment':
        if not (args.emails or args.names):
            parser.error(
                'Either --email or --name must be passed at least once'
            )
        else:
            db = AccountDatabase()
            for email in args.emails:
                try:
                    account = db.get_account(email=email)
                except exceptions.AccountDoesNotExistException:
                    print(f'[ERROR] Account `{email}` does not exist')
                else:
                    db.change_update(
                        account['id'], datetime_signed=None, office_signed=None
                    )
                    print(
                        f"[SUCCESS] Account's `{email}` "
                        "appointment has been deleted"
                    )
            for name in args.names:
                try:
                    dependent = db.get_dependent(dependent_name=name)
                except exceptions.DependentDoesNotExistException:
                    print(f'[ERROR] Dependent `{name}` does not exist')
                else:
                    db.change_dependent(
                        dependent['id'], 
                        datetime_signed=None, office_signed=None
                    )
                    print(
                        f"[SUCCESS] Dependents's `{name}` "
                        "appointment has been deleted"
                    )
