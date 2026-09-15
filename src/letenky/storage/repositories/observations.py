class ObservationRepository:
    def __init__(self, database):
        self.database = database

    def history(self, watch_id):
        with self.database.connect() as db:
            return [dict(row) for row in db.execute("""SELECT c.finished_at,c.status,c.error,
                p.observed_at,p.amount_minor,p.currency,p.source_updated_at
                FROM check_runs c LEFT JOIN price_observations p ON p.check_run_id=c.id
                WHERE c.watch_id=? ORDER BY c.id""", (watch_id,))]
