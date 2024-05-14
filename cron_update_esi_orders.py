"""
Updates market orders. In it's own file for CRON jobs.
"""
import janitor

janitor.update_orders_data()
