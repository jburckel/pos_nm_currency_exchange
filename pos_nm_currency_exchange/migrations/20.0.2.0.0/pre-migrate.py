# -*- coding: utf-8 -*-


def migrate(cr, version):
    """20.0.2.0.0: the operations record the user who made them. Fill the
    new column from the creator before the ORM creates it, else it would
    take its default, the user running the upgrade. Safe to run again."""
    if not version:
        return
    cr.execute("ALTER TABLE pos_nm_exchange ADD COLUMN IF NOT EXISTS user_id int4")
    cr.execute("UPDATE pos_nm_exchange SET user_id = create_uid WHERE user_id IS NULL")
