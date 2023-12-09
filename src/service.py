class Service:
    def __init__(self, db):
        self.db = db

    def get_world_list(self):
        sql = "SELECT world_id, name FROM world_info ORDER BY name ASC"
        return self.db.query(sql)

    def get_match_list(self, world_id):
        sql = """
            SELECT
                DISTINCT zone_id
            FROM
                death_event e
            WHERE
                e.world_id = :world_id
                AND e.zone_id > 1000
            ORDER BY
                e.zone_id DESC
        """

        return self.db.query(sql, {"world_id": world_id})

    def get_character_list(self, world_id, zone_id):
        sql = """
            SELECT
                DISTINCT COALESCE(o.alias, o.name, c.outfit_id::varchar) AS outfit,
                COALESCE(c.name, e.character_id::varchar) AS name,
                c.character_id
            FROM death_event e
                LEFT JOIN character_info c ON e.character_id = c.character_id
                LEFT JOIN outfit_info o ON c.outfit_id = o.outfit_id
            WHERE
                e.world_id = :world_id
                AND e.zone_id = :zone_id
            ORDER BY
                outfit, name
        """

        return self.db.query(sql, {"world_id": world_id, "zone_id": zone_id})

    def get_vehicle_kills(self, world_id, zone_id, character_ids):
        params = {"world_id": world_id, "zone_id": zone_id}

        sql = """
            SELECT
                COUNT(1) AS num,
                COALESCE(attacker_outfit.alias, attacker.outfit_id::varchar) AS attacker_outfit,
                COALESCE(defender_outfit.alias, defender.outfit_id::varchar) AS defender_outfit,
                defender_vehicle_info.name AS vehicle_name,
                defender_vehicle_info.vehicle_id AS vehicle_id,
                defender_vehicle_info.category AS vehicle_category,
                e.character_id = e.attacker_character_id AS is_suicide
            FROM vehicle_destroy_event e
                LEFT JOIN character_info defender ON e.character_id = defender.character_id
                LEFT JOIN outfit_info defender_outfit ON defender.outfit_id = defender_outfit.outfit_id
                LEFT JOIN character_info attacker ON e.attacker_character_id = attacker.character_id
                LEFT JOIN outfit_info attacker_outfit ON attacker.outfit_id = attacker_outfit.outfit_id
                JOIN vehicle_info defender_vehicle_info ON e.character_vehicle_id = defender_vehicle_info.vehicle_id
            WHERE
                e.world_id = :world_id
                AND e.zone_id = :zone_id
        """

        if character_ids:
            sql += " AND ("
            sql += " OR ".join([f"e.character_id = :character_id{idx} OR e.attacker_character_id = :character_id{idx}" for idx, q in enumerate(character_ids)])
            sql += ")"
            for idx, q in enumerate(character_ids):
                params[f"character_id{idx}"] = q

        sql += """
            GROUP BY
                attacker.outfit_id,
                defender.outfit_id,
                attacker_outfit.alias,
                defender_outfit.alias,
                defender_vehicle_info.name,
                defender_vehicle_info.vehicle_id,
                defender_vehicle_info.category,
                is_suicide
            ORDER BY
                vehicle_name DESC
        """

        return self.db.query(sql, params)

    def get_infantry_stats(self, world_id, zone_id, character_ids):
        params = {"world_id": world_id, "zone_id": zone_id}

        sql = """
            SELECT
                COUNT(1) AS num,
                COALESCE(outfit.alias, c.outfit_id::varchar) AS outfit,
                e.experience_id,
                xp.description AS action
            FROM gain_experience_event e
                LEFT JOIN character_info c ON e.character_id = c.character_id
                LEFT JOIN outfit_info outfit ON c.outfit_id = outfit.outfit_id
                LEFT JOIN experience_info xp ON e.experience_id = xp.experience_id
            WHERE
                e.world_id = :world_id
                AND e.zone_id = :zone_id
                AND e.experience_id IN (1, 2, 3, 4, 5, 6, 7, 37, 51, 53, 56, 30, 142, 201, 233, 277, 335, 355, 592)
        """

        if character_ids:
            sql += " AND ( "
            sql += " OR ".join([f"e.character_id = :character_id{idx}" for idx, q in enumerate(character_ids)])
            sql += " ) "
            for idx, q in enumerate(character_ids):
                params[f"character_id{idx}"] = q

        sql += """
            GROUP BY
                c.outfit_id,
                outfit.alias,
                e.experience_id,
                xp.description
        """

        return self.db.query(sql, params)

    def get_outfit_stats(self, world_id, zone_id, character_ids):
        params = {"world_id": world_id, "zone_id": zone_id}

        sql = """
            SELECT
                COALESCE(o.alias, c.outfit_id::varchar) AS outfit,
                f.alias AS faction,
                COUNT(1) as num_players,
                ROUND(AVG(c.battle_rank * (1 + c.is_prestige))) AS avg_battle_rank,
                ROUND(AVG(c.minutes_played) / 60) AS avg_hours_played,
                ROUND((extract(epoch from now()) - AVG(c.created_at)) / 86400) AS avg_player_age_days,
                ROUND((extract(epoch from now()) - AVG(c.member_since)) / 86400) AS avg_member_age_days
            FROM (
                    SELECT
                        e.character_id
                    FROM gain_experience_event e
                    WHERE
                        e.world_id = :world_id
                        AND e.zone_id = :zone_id
                    GROUP BY
                      e.character_id
                ) t
                LEFT JOIN character_info c ON t.character_id = c.character_id
                LEFT JOIN outfit_info o ON c.outfit_id = o.outfit_id
                LEFT JOIN faction_info f ON o.faction_id = f.faction_id
        """

        if character_ids:
            sql += " WHERE "
            sql += " OR ".join([f"t.character_id = :character_id{idx}" for idx, q in enumerate(character_ids)])
            for idx, q in enumerate(character_ids):
                params[f"character_id{idx}"] = q

        sql += """
            GROUP BY
                o.alias,
                c.outfit_id,
                faction
            ORDER BY
                o.alias
        """

        return self.db.query(sql, params)

    def get_kills_by_weapon(self, world_id, zone_id, character_ids):
        params = {"world_id": world_id, "zone_id": zone_id}

        sql = """
            SELECT
                COALESCE(w.name, CASE WHEN e.attacker_weapon_id = 0 THEN 'Ram/Roadkill/Fall' ELSE e.attacker_weapon_id::varchar END) AS weapon,
                attacker_vehicle_info.name AS vehicle_name,
                COALESCE(attacker_outfit.alias, attacker.outfit_id::varchar) AS attacker_outfit,
                COUNT(1) AS kills,
                SUM(e.is_headshot) AS num_headshot,
                SUM(CASE WHEN defender_outfit.alias = attacker_outfit.alias THEN 1 ELSE 0 END) AS team_kills,
                SUM(CASE WHEN e.character_id = e.attacker_character_id THEN 1 ELSE 0 END) AS suicides
            FROM death_event e
                LEFT JOIN weapon_info w ON e.attacker_weapon_id = w.item_id
                LEFT JOIN character_info defender ON e.character_id = defender.character_id
                LEFT JOIN outfit_info defender_outfit ON defender.outfit_id = defender_outfit.outfit_id
                LEFT JOIN character_info attacker ON e.attacker_character_id = attacker.character_id
                LEFT JOIN outfit_info attacker_outfit ON attacker.outfit_id = attacker_outfit.outfit_id
                LEFT JOIN vehicle_info attacker_vehicle_info ON e.attacker_vehicle_id = attacker_vehicle_info.vehicle_id
            WHERE
                e.world_id = :world_id
                AND e.zone_id = :zone_id
        """

        if character_ids:
            sql += " AND ("
            sql += " OR ".join([f"e.character_id = :character_id{idx} OR e.attacker_character_id = :character_id{idx}" for idx, q in enumerate(character_ids)])
            sql += ")"
            for idx, q in enumerate(character_ids):
                params[f"character_id{idx}"] = q

        sql += """
            GROUP BY
                attacker.outfit_id,
                e.attacker_weapon_id,
                attacker_outfit.alias,
                attacker_vehicle_info.name,
                w.name
        """

        return self.db.query(sql, params)

    def get_vehicle_deaths_by_weapon(self, world_id, zone_id, character_ids):
        params = {"world_id": world_id, "zone_id": zone_id}

        sql = """
            SELECT
                COALESCE(w.name, CASE WHEN e.attacker_weapon_id = 0 THEN 'Ram/Roadkill/Fall' ELSE e.attacker_weapon_id::varchar END) AS weapon,
                defender_vehicle_info.name AS vehicle_name,
                COALESCE(defender_outfit.alias, defender.outfit_id::varchar) AS defender_outfit,
                COUNT(1) AS deaths,
                SUM(CASE WHEN defender_outfit.alias = attacker_outfit.alias THEN 1 ELSE 0 END) AS team_deaths,
                SUM(CASE WHEN e.character_id = e.attacker_character_id THEN 1 ELSE 0 END) AS suicides
            FROM vehicle_destroy_event e
                LEFT JOIN weapon_info w ON e.attacker_weapon_id = w.item_id
                LEFT JOIN character_info defender ON e.character_id = defender.character_id
                LEFT JOIN outfit_info defender_outfit ON defender.outfit_id = defender_outfit.outfit_id
                LEFT JOIN character_info attacker ON e.attacker_character_id = attacker.character_id
                LEFT JOIN outfit_info attacker_outfit ON attacker.outfit_id = attacker_outfit.outfit_id
                JOIN vehicle_info defender_vehicle_info ON e.character_vehicle_id = defender_vehicle_info.vehicle_id
            WHERE
                e.world_id = :world_id
                AND e.zone_id = :zone_id
        """

        if character_ids:
            sql += " AND ("
            sql += " OR ".join([f"e.character_id = :character_id{idx} OR e.attacker_character_id = :character_id{idx}" for idx, q in enumerate(character_ids)])
            sql += ")"
            for idx, q in enumerate(character_ids):
                params[f"character_id{idx}"] = q

        sql += """
            GROUP BY
                defender.outfit_id,
                e.attacker_weapon_id,
                defender_outfit.alias,
                defender_vehicle_info.name,
                w.name
        """

        return self.db.query(sql, params)
