##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


# context managers for transaction and state commit/rollback
from contextlib import contextmanager

import transaction

# define exception type to catch cases where current transaction is explicitly
# committed or aborted with in the body of the with statement (only necessary on
# abort)
class InvalidTransactionError(Exception): pass

@contextmanager
def zodb_transaction():
    try:
        txn = transaction.get()
        yield txn
    except Exception:
        if txn is not transaction.get():
            raise InvalidTransactionError(
                "could not abort transaction, was already aborted/committed within 'with' body")
        try:
            txn.abort()
        # catch any internal exceptions that happen during abort
        except Exception:
            pass
        raise
    else:
        try:
            if txn is transaction.get():
                txn.commit()
        # catch any internal exceptions that happen during commit
        except Exception:
            pass

@contextmanager
def nested_transaction(xaDataManager=None):
    try:
        txn = transaction.get()
        sp = txn.savepoint()
        if xaDataManager is not None:
            txn.join(xaDataManager)
        yield
    except Exception:
        try:
            sp.rollback()
            if xaDataManager is not None:
                xaDataManager.abort(txn)
        except Exception:
            pass
        raise
    else:
        pass
