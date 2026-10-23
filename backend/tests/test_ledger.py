from app.finance.ledger import Account, JournalEntry, Ledger, LedgerError, LedgerLine


def test_ledger_rejects_unbalanced_entries_and_keeps_books_balanced():
    ledger = Ledger()
    ledger.seed_cash("cafe", 100_000)
    try:
        ledger.post(JournalEntry("bad", "cafe", (LedgerLine(Account.CASH, 10, "cafe"),)))
    except LedgerError:
        pass
    else:
        raise AssertionError("unbalanced entry should be rejected")
    assert ledger.is_balanced()
    assert ledger.balance("cafe") == 100_000


def test_ledger_idempotency_is_a_noop():
    ledger = Ledger()
    entry = JournalEntry("opening", "cafe", (LedgerLine(Account.CASH, 100, "cafe"), LedgerLine(Account.EQUITY, -100, "cafe")), idempotency_key="opening:cafe")
    assert ledger.post(entry) is ledger.post(entry)
    assert len(ledger.entries) == 1

