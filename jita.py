"""
Jita station trader
"""
import os
import sqlite3

def items_h(h):
    """
    Gets the items that made the most money in the last {h} hours.
    """

    cwd = os.getcwd()
    conn = sqlite3.connect(cwd+"/market/volume/10000002.db")
    cur = conn.cursor()

    cmd = f"""
    SELECT 
        type_id,
        eff_volume as vol,
        (av_sell-(av_buy * 1.08)) * eff_volume as profit        
    FROM (
        SELECT
            type_id,
            sum(sell_value)/sum(sell_volume) as av_sell,
            sum(buy_value)/sum(buy_volume) as av_buy,
            (CASE WHEN sum(sell_volume) > sum(buy_volume) THEN sum(buy_volume) ELSE sum(sell_volume) END) as eff_volume
        FROM events
        WHERE   system_id = 30000142 AND
                strftime('%s') - timestamp < {h}*60*60
        GROUP BY type_id
    ) AS temp
    GROUP BY type_id 
    ORDER BY profit DESC;
    """
    cur.execute(cmd)
    res = cur.fetchall()
    conn.close()
    return res
