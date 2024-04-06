"""
Determines the volume difference from historical data
"""

def difference():
    """
    Goes though regional order databases. Calculates historical volume
    from different saved order sets. Deletes old order sets if necessary.

    type_id, system_id, is_buy, volume, interval_sec, timestamp
        /market/volume/volume.db
            table : id10000042 (for each region)
    
    type_id, region_id, is_buy, daily_estimate
        /market/volume/volume.db
            table : index

    Index houses the look up for item daily interaction estimates.
    """
    pass