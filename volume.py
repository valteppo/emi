"""
Determines the volume difference from historical data
"""
import os
import sqlite3

def difference():
    """
    Goes though regional order databases. Calculates historical volume
    from different saved order sets. 
    """
    ## SQL magic
    # Finds the differences in volume between order sets
    """
        SELECT 
            new.type_id AS type_id, 
            new.is_buy_order AS is_buy_order, 
            (old.volume_remain - new.volume_remain) AS volume_change,
            (old.volume_remain - new.volume_remain) * new.price AS interaction_value
        FROM new 
        INNER JOIN 
            old ON old.order_id = new.order_id 
        WHERE old.volume_remain != new.volume_remain
    """
    
    # Finds the completed orders (old orders not present in new order set)
    """
        SELECT
            old.type_id AS type_id, 
            old.is_buy_order AS is_buy_order, 
            old.volume_remain AS volume_change,
            (old.volume_remain * old.price) AS interaction_value
        FROM old
        WHERE old.order_id NOT IN (SELECT new.order_id FROM new);
    """

    # Find the newly issued orders that have sold few items already
    """
        SELECT
            new.type_id AS type_id, 
            new.is_buy_order AS is_buy_order, 
            (new.volume_total - new.volume_remain) AS volume_change,
            ((new.volume_total - new.volume_remain) * new.price) AS interaction_value
        FROM new
        WHERE new.order_id NOT IN (SELECT old.order_id 
                                    FROM old)
                AND
                new.volume_total != new.volume_remain;

    """
    # Combined search of sell and buy events:
    """
        SELECT 
            new.system_id as system_id,
            new.type_id AS type_id, 
            new.is_buy_order AS is_buy_order, 
            (old.volume_remain - new.volume_remain) AS volume_change,
            ((old.volume_remain - new.volume_remain) * new.price) AS interaction_value
        FROM new 
        INNER JOIN 
            old ON old.order_id = new.order_id 
        WHERE old.volume_remain != new.volume_remain
        UNION ALL
        SELECT
            old.system_id as system_id,
            old.type_id AS type_id, 
            old.is_buy_order AS is_buy_order, 
            old.volume_remain AS volume_change,
            (old.volume_remain * old.price) AS interaction_value
        FROM old
        WHERE old.order_id NOT IN (SELECT new.order_id 
                                    FROM new)
        UNION ALL
        SELECT
            new.system_id as system_id,
            new.type_id AS type_id, 
            new.is_buy_order AS is_buy_order, 
            (new.volume_total - new.volume_remain) AS volume_change,
            ((new.volume_total - new.volume_remain) * new.price) AS interaction_value
        FROM new
        WHERE new.order_id NOT IN (SELECT old.order_id 
                                    FROM old)
                AND
                new.volume_total != new.volume_remain;
    """

    # Sell and buy events summarized, by system, by type_id
    """
    SELECT
        system_id,
        type_id,
        SUM(CASE WHEN is_buy_order = 1 THEN volume_change ELSE 0 END) AS buy_volume,
        SUM(CASE WHEN is_buy_order = 0 THEN volume_change ELSE 0 END) AS sell_volume,
        SUM(CASE WHEN is_buy_order = 1 THEN interaction_value ELSE 0 END) AS buy_value,
        SUM(CASE WHEN is_buy_order = 0 THEN interaction_value ELSE 0 END) AS sell_value,
        strftime('%s', 'now') AS timestamp
        FROM (
                SELECT 
                new.system_id as system_id,
                new.type_id AS type_id, 
                new.is_buy_order AS is_buy_order, 
                (old.volume_remain - new.volume_remain) AS volume_change,
                ((old.volume_remain - new.volume_remain) * new.price) AS interaction_value
            FROM new 
            INNER JOIN 
                old ON old.order_id = new.order_id 
            WHERE old.volume_remain != new.volume_remain
            UNION ALL
            SELECT
                old.system_id as system_id,
                old.type_id AS type_id, 
                old.is_buy_order AS is_buy_order, 
                old.volume_remain AS volume_change,
                (old.volume_remain * old.price) AS interaction_value
            FROM old
            WHERE old.order_id NOT IN (SELECT new.order_id 
                                        FROM new)
            UNION ALL
            SELECT
                new.system_id as system_id,
                new.type_id AS type_id, 
                new.is_buy_order AS is_buy_order, 
                (new.volume_total - new.volume_remain) AS volume_change,
                ((new.volume_total - new.volume_remain) * new.price) AS interaction_value
            FROM new
            WHERE new.order_id NOT IN (SELECT old.order_id 
                                        FROM old)
                    AND
                    new.volume_total != new.volume_remain
        ) AS temp_table
    GROUP BY system_id, type_id;    
    """

    cwd = os.getcwd()
    order_databases = os.listdir(cwd+"/market/orders/")

    def conduit(target_database_name):
        """
        Transfers order difference to volume database
        """
        cwd = os.getcwd()
        source_conn = sqlite3.connect(cwd+"/market/orders/"+target_database_name)
        source_cur = source_conn.cursor()

        source_cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name DESC")
        tables = [i[0] for i in source_cur.fetchall()]
        if len(tables) < 2:
            return

        target_conn = sqlite3.connect(cwd+"/market/volume/"+target_database_name)
        target_cur = target_conn.cursor()

        new = tables[0]
        old = tables[1]
        time_difference = int(new[len("unix"):]) - int(old[len("unix"):])
        difference_cmd = f"""
        SELECT
            system_id,
            type_id,
            SUM(CASE WHEN is_buy_order = 1 THEN volume_change ELSE 0 END) AS buy_volume,
            SUM(CASE WHEN is_buy_order = 0 THEN volume_change ELSE 0 END) AS sell_volume,
            SUM(CASE WHEN is_buy_order = 1 THEN interaction_value ELSE 0 END) AS buy_value,
            SUM(CASE WHEN is_buy_order = 0 THEN interaction_value ELSE 0 END) AS sell_value
        FROM (
            SELECT 
                {new}.system_id as system_id,
                {new}.type_id AS type_id, 
                {new}.is_buy_order AS is_buy_order, 
                ({old}.volume_remain - {new}.volume_remain) AS volume_change,
                (({old}.volume_remain - {new}.volume_remain) * {new}.price) AS interaction_value
            FROM {new} 
            INNER JOIN 
                {old} ON {old}.order_id = {new}.order_id 
            WHERE {old}.volume_remain != {new}.volume_remain
            UNION ALL
            SELECT
                {old}.system_id as system_id,
                {old}.type_id AS type_id, 
                {old}.is_buy_order AS is_buy_order, 
                {old}.volume_remain AS volume_change,
                ({old}.volume_remain * {old}.price) AS interaction_value
            FROM {old}
            WHERE {old}.order_id NOT IN (SELECT {new}.order_id FROM {new})
            UNION ALL
            SELECT
                {new}.system_id as system_id,
                {new}.type_id AS type_id, 
                {new}.is_buy_order AS is_buy_order, 
                ({new}.volume_total - {new}.volume_remain) AS volume_change,
                (({new}.volume_total - {new}.volume_remain) * {new}.price) AS interaction_value
            FROM {new}
            WHERE {new}.order_id NOT IN (SELECT {old}.order_id FROM {old})
                AND
                {new}.volume_total != {new}.volume_remain
        ) AS temp_table
        GROUP BY system_id, type_id;
        """

        source_cur.execute(difference_cmd)
        difference_results = source_cur.fetchall()
        source_conn.close()
            
        target_deposit_cmd = f"""CREATE TABLE IF NOT EXISTS 
                                events (system_id int, 
                                        type_id int, 
                                        buy_volume int, 
                                        sell_volume int, 
                                        buy_value float, 
                                        sell_value float, 
                                        interval int,
                                        timestamp int)"""
        target_cur.execute(target_deposit_cmd)
        target_deposit_cmd = """INSERT INTO events (
                                    system_id, 
                                    type_id, 
                                    buy_volume, 
                                    sell_volume, 
                                    buy_value, 
                                    sell_value, 
                                    interval,
                                    timestamp
                                )
                                VALUES (
                                    ?,?,?,?,?,?,?, strftime('%s', 'now')
                                )
                            """
        for line in difference_results:
            line_data = [i for i in line]
            line_data.append(time_difference)
            target_cur.execute(target_deposit_cmd, line_data)
        target_conn.commit()
        target_conn.close()

    for database in order_databases:
        conduit(database)

def volume_transfer():
    """
    Moves the volume folder to transfer folder.
    """
    cwd = os.getcwd()
    for file in os.listdir(cwd+"/market/volume"):
        os.popen(f'cp {cwd+"/market/volume/"+file} {cwd+"/transfer/market/volume/"+file}') 

volume_transfer()