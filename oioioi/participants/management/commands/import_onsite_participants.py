from __future__ import print_function

import csv
import os

import urllib.request
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, transaction
from django.utils.translation import gettext as _

from oioioi.contests.models import Contest
from oioioi.participants.admin import OnsiteRegistrationParticipantAdmin
from oioioi.participants.models import OnsiteRegistration, Participant, Region


class Command(BaseCommand):
    COLUMNS = ['number', 'username', 'region_short_name', 'local_number']
    columns_str = ', '.join(COLUMNS)

    help = _(
        "Updates the list of participants of <contest_id> from the given "
        "CSV file <filename or url>, with the following columns: "
        "%(columns)s.\n\n"
        "Given CSV file should contain a header row with column names "
        "(respectively %(columns)s) separated by commas. Following rows "
        "should contain participant data."
    ) % {'columns': columns_str}

    requires_model_validation = True

    def add_arguments(self, parser):
        parser.add_argument('contest_id', type=str, help='Contest to import to')
        parser.add_argument('filename_or_url', type=str, help='Source CSV file')

    def handle(self, *args, **options):
        try:
            contest = Contest.objects.get(id=options['contest_id'])
        except Contest.DoesNotExist:
            raise CommandError(_("Contest %s does not exist") % options['contest_id'])

        rcontroller = contest.controller.registration_controller()
        print(rcontroller)
        if not issubclass(
            getattr(rcontroller, 'participant_admin', None),
            OnsiteRegistrationParticipantAdmin,
        ):
            raise CommandError(_("Wrong type of contest"))

        arg = options['filename_or_url']

        if arg.startswith('http://') or arg.startswith('https://'):
            self.stdout.write(_("Fetching %s...\n") % (arg,))
            stream = urllib.request.urlopen(arg)
        else:
            if not os.path.exists(arg):
                raise CommandError(_("File not found: %s") % arg)
            stream = open(arg, 'r')

        reader = csv.reader(stream)
        header = next(reader)
        if header != self.COLUMNS:
            raise CommandError(
                _(
                    "Missing header or invalid columns: "
                    "%(header)s\nExpected: %(expected)s"
                )
                % {'header': ', '.join(header), 'expected': ', '.join(self.COLUMNS)}
            )

        with transaction.atomic():
            ok = True
            all_count = 0
            for row in reader:
                all_count += 1

                for i, _column in enumerate(self.COLUMNS):
                    if not isinstance(row[i], str):
                        row[i] = row[i].decode('utf8')

                try:
                    user = User.objects.get(username=row[1])
                    region = Region.objects.get(short_name=row[2], contest=contest)

                    participant, created = Participant.objects.get_or_create(
                        contest=contest, user=user
                    )

                    reg = OnsiteRegistration(
                        participant=participant,
                        number=row[0],
                        local_number=row[3],
                        region=region,
                    )

                    reg.full_clean()
                    reg.save()
                except User.DoesNotExist:
                    self.stdout.write(
                        _("Error for user=%(user)s: user does not exist\n")
                        % {'user': row[1]}
                    )
                    ok = False
                except Region.DoesNotExist:
                    self.stdout.write(
                        _(
                            "Error for user=%(user)s: region %(region)s does"
                            " not exist\n"
                        )
                        % {'user': row[1], 'region': row[2]}
                    )
                    ok = False
                except DatabaseError as e:
                    # This assumes that we'll get the message in this
                    # encoding. It is not perfect, but much better than
                    # ascii.
                    message = e.message.decode('utf-8')
                    self.stdout.write(
                        _("DB Error for user=%(user)s: %(message)s\n")
                        % {'user': row[1], 'message': message}
                    )
                    ok = False
                except ValidationError as e:
                    for k, v in e.message_dict.items():
                        for message in v:
                            if k == '__all__':
                                self.stdout.write(
                                    _("Error for user=%(user)s: %(message)s\n")
                                    % {'user': row[1], 'message': message}
                                )
                            else:
                                self.stdout.write(
                                    _(
                                        "Error for user=%(user)s, "
                                        "field %(field)s: %(message)s\n"
                                    )
                                    % {'user': row[1], 'field': k, 'message': message}
                                )
                    ok = False

            if ok:
                self.stdout.write(_("Processed %d entries") % (all_count))
            else:
                raise CommandError(_("There were some errors. Database not changed.\n"))
