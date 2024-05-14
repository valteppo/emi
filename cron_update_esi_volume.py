"""
Updates esi volume. In it's own file for CRON jobs.
"""
import janitor

janitor.download_volume_histories()