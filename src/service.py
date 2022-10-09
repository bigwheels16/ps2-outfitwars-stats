class Service:
    def __init__(self, db):
        self.db = db

    def get_world_list(self):
        sql = "SELECT world_id, name FROM world_info ORDER BY name ASC"
        return self.db.query(sql)

    def get_match_list(self, world_id):
        sql = "SELECT DISTINCT match_id FROM death_event WHERE world_id = ? AND match_id != 0"
        return self.db.query(sql, [world_id])

    def get_character_list(self, world_id, match_id):
        sql = "SELECT DISTINCT COALESCE(o.alias, o.name, o.outfit_id) AS outfit, c.name, c.character_id " \
              "FROM death_event e " \
              "LEFT JOIN character_info c ON e.character_id = c.character_id " \
              "LEFT JOIN outfit_info o ON c.outfit_id = o.outfit_id " \
              "WHERE e.world_id = ? AND e.match_id = ? " \
              "ORDER BY outfit, c.name"
        return self.db.query(sql, [world_id, match_id])

    def get_vehicle_kills(self, world_id, match_id, character_id):
        params = [world_id, match_id]

        sql = "SELECT COUNT(1) AS num, attacker_outfit.alias AS attacker_outfit, " \
              "defender_outfit.alias AS defender_outfit, defender_vehicle_info.name AS vehicle_name, " \
              "defender_vehicle_info.vehicle_id AS vehicle_id, defender_vehicle_info.category AS vehicle_category," \
              "e.character_id = e.attacker_character_id AS is_suicide  " \
              "FROM vehicle_destroy_event e " \
              "LEFT JOIN character_info defender ON e.character_id = defender.character_id " \
              "LEFT JOIN outfit_info defender_outfit ON defender.outfit_id = defender_outfit.outfit_id " \
              "LEFT JOIN character_info attacker ON e.attacker_character_id = attacker.character_id " \
              "LEFT JOIN outfit_info attacker_outfit ON attacker.outfit_id = attacker_outfit.outfit_id " \
              "JOIN vehicle_info defender_vehicle_info ON e.character_vehicle_id = defender_vehicle_info.vehicle_id " \
              "WHERE e.world_id = ? AND e.match_id = ? "

        if character_id:
            sql += " AND (e.character_id = ? OR e.attacker_character_id = ?) "
            params.append(character_id)
            params.append(character_id)

        sql += "GROUP BY attacker_outfit.alias, defender_outfit.alias, defender_vehicle_info.name, " \
               "defender_vehicle_info.vehicle_id, defender_vehicle_info.category, is_suicide " \
               "ORDER BY vehicle_name DESC"
        return self.db.query(sql, params)

    def get_infantry_stats(self, world_id, match_id, character_id):
        params = [world_id, match_id]

        sql = "SELECT COUNT(1) AS num, outfit.alias AS outfit, e.experience_id, xp.description AS action " \
              "FROM gain_experience_event e " \
              "LEFT JOIN character_info c ON e.character_id = c.character_id " \
              "LEFT JOIN outfit_info outfit ON c.outfit_id = outfit.outfit_id " \
              "LEFT JOIN experience_info xp ON e.experience_id = xp.experience_id " \
              "WHERE e.world_id = ? AND e.match_id = ? AND e.experience_id IN (1, 2, 3, 4, 5, 6, 7, 37, 51, 53, 56, 30, 142, 201, 233, 277, 335, 355, 592) "

        if character_id:
            sql += " AND e.character_id = ? "
            params.append(character_id)

        sql += "GROUP BY outfit.alias, e.experience_id, xp.description"

        return self.db.query(sql, params)

    def get_kills_by_weapon(self, world_id, match_id, character_id):
        params = [world_id, match_id]

        sql = "SELECT COALESCE(w.name, IF(e.attacker_weapon_id = 0, 'Ram/Roadkill/Fall', e.attacker_weapon_id)) AS weapon, " \
              "attacker_vehicle_info.name AS vehicle_name, " \
              "attacker_outfit.alias AS attacker_outfit, " \
              "COUNT(1) AS kills, " \
              "SUM(e.is_headshot) AS num_headshot, " \
              "SUM(IF(defender_outfit.alias = attacker_outfit.alias, 1, 0)) AS team_kills, " \
              "SUM(IF(e.character_id = e.attacker_character_id, 1, 0)) AS suicides " \
              "FROM death_event e " \
              "LEFT JOIN weapon_info w ON e.attacker_weapon_id = w.item_id " \
              "LEFT JOIN character_info defender ON e.character_id = defender.character_id " \
              "LEFT JOIN outfit_info defender_outfit ON defender.outfit_id = defender_outfit.outfit_id " \
              "LEFT JOIN character_info attacker ON e.attacker_character_id = attacker.character_id " \
              "LEFT JOIN outfit_info attacker_outfit ON attacker.outfit_id = attacker_outfit.outfit_id " \
              "LEFT JOIN vehicle_info attacker_vehicle_info ON e.attacker_vehicle_id = attacker_vehicle_info.vehicle_id " \
              "WHERE e.world_id = ? AND e.match_id = ? "

        if character_id:
            sql += " AND (e.character_id = ? OR e.attacker_character_id = ?) "
            params.append(character_id)
            params.append(character_id)

        sql += "GROUP BY e.attacker_weapon_id, attacker_outfit.alias, attacker_vehicle_info.name, w.name "

        return self.db.query(sql, params)

    def get_vehicle_deaths_by_weapon(self, world_id, match_id, character_id):
        params = [world_id, match_id]

        sql = "SELECT COALESCE(w.name, IF(e.attacker_weapon_id = 0, 'Ram/Roadkill/Fall', e.attacker_weapon_id)) AS weapon, " \
              "defender_vehicle_info.name AS vehicle_name, " \
              "defender_outfit.alias AS defender_outfit, " \
              "COUNT(1) AS deaths, " \
              "SUM(IF(defender_outfit.alias = attacker_outfit.alias, 1, 0)) AS team_deaths, " \
              "SUM(IF(e.character_id = e.attacker_character_id, 1, 0)) AS suicides " \
              "FROM vehicle_destroy_event e " \
              "LEFT JOIN weapon_info w ON e.attacker_weapon_id = w.item_id " \
              "LEFT JOIN character_info defender ON e.character_id = defender.character_id " \
              "LEFT JOIN outfit_info defender_outfit ON defender.outfit_id = defender_outfit.outfit_id " \
              "LEFT JOIN character_info attacker ON e.attacker_character_id = attacker.character_id " \
              "LEFT JOIN outfit_info attacker_outfit ON attacker.outfit_id = attacker_outfit.outfit_id " \
              "LEFT JOIN vehicle_info defender_vehicle_info ON e.character_vehicle_id = defender_vehicle_info.vehicle_id " \
              "WHERE e.world_id = ? AND e.match_id = ? "

        if character_id:
            sql += " AND (e.character_id = ? OR e.attacker_character_id = ?) "
            params.append(character_id)
            params.append(character_id)

        sql += "GROUP BY e.attacker_weapon_id, defender_outfit.alias, defender_vehicle_info.name, w.name "

        return self.db.query(sql, params)

    def get_damage(self, version, weapons, targets, directions):
        if not weapons:
            return []

        params = [version]
        sql = """
            SELECT w.max_damage, w.min_damage, r.value AS resist_value, t.name AS target_name, w.name AS weapon_name, t.health,
            COALESCE(a.value, 1) AS armor_value, COALESCE(a2.name, 'Direct') AS attack_direction, w.damage_type_id, w.indirect_damage_type_id,
            w.indirect_damage, COALESCE(r2.value, 0) AS indirect_resist_value,
            CASE WHEN w.is_flak = 1 AND t.is_flak_damage = 1 THEN 0 ELSE 1 END AS include_direct_damage
            FROM weapon w
            JOIN damage_resistance r ON (w.damage_type_id = r.damage_type_id AND w.version_id = r.version_id)
            JOIN target t ON (r.target_id = t.target_id AND r.version_id = t.version_id)
            LEFT JOIN damage_resistance r2 ON (t.target_id = r2.target_id AND w.indirect_damage_type_id = r2.damage_type_id AND t.version_id = r2.version_id)
            LEFT JOIN vehicle_armor a ON (t.target_id = a.target_id AND t.version_id = a.version_id)
            LEFT JOIN attack_direction a2 ON (a.attack_direction_id = a2.id)
            WHERE w.version_id = ?
        """

        if weapons:
            sql += " AND ("
            sql += " OR ".join(["w.weapon_id = ?" for q in weapons])
            sql += ")"
            for q in weapons:
                params.append(q)

        if targets:
            sql += " AND ("
            sql += " OR ".join(["t.target_id = ?" for q in targets])
            sql += ")"
            for q in targets:
                params.append(q)

        if directions:
            sql += " AND ("
            sql += " OR ".join(["a2.id = ?" for q in directions])
            sql += ")"
            for q in directions:
                params.append(q)

        rows = self.db.query(sql, params)

        data = []
        for row in rows:
            data.append(row)

        return data
