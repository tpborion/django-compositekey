from __future__ import absolute_import

from django.db import transaction, IntegrityError, DatabaseError
from django.test import TestCase

from .models import (Counter, WithCustomPK, InheritedCounter, ProxyCounter,
                     SubCounter)


class ForceTests(TestCase):
    def test_force_update(self):
        c = Counter.objects.create(name="one", name2="ONE", value=1)

        # The normal case
        c.value = 2
        c.save()
        # Same thing, via an update
        c.value = 3
        c.save(force_update=True)

        # Won't work because force_update and force_insert are mutually
        # exclusive
        c.value = 4
        self.assertRaises(ValueError, c.save, force_insert=True, force_update=True)

        # Try to update something that doesn't have a primary key in the first
        # place.
        c1 = Counter(name="two", name2="TWO", value=2)
        self.assertRaises(DatabaseError, c1.save, force_update=True)
        c1.save(force_insert=True)

        # Won't work because we can't insert a pk of the same value.
        sid = transaction.savepoint()
        c.value = 5
        self.assertRaises(IntegrityError, c.save, force_insert=True)
        transaction.savepoint_rollback(sid)

        # Trying to update should still fail, even with manual primary keys, if
        # the data isn't in the database already.
        obj = WithCustomPK(name=1, value=1)
        self.assertRaises(DatabaseError, obj.save, force_update=True)


class InheritanceTests(TestCase):
    def test_force_update_on_inherited_model(self):
        a = InheritedCounter(name="count", name2="COUNT", value=1, tag="spam")
        a.save()
        a.save(force_update=True)

    def test_force_update_on_proxy_model(self):
        a = ProxyCounter(name="count", name2="COUNT", value=1)
        a.save()
        a.save(force_update=True)

    def test_force_update_on_inherited_model_without_fields(self):
        '''
        Issue 13864: force_update fails on subclassed models, if they don't
        specify custom fields.
        '''
        a = SubCounter(name="count", name2="COUNT", value=1)
        a.save()
        a.value = 2
        a.save(force_update=True)
