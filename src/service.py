import config
import db

db = db.DB()
db.connect_mysql(config.DB_HOST(),
                 config.DB_PORT(),
                 config.DB_USERNAME(),
                 config.DB_PASSWORD(),
                 config.DB_DATABASE())


class Service:
    def __init__(self):
        pass

    def get_world_list(self):
        sql = "SELECT world_id, name FROM world_info ORDER BY name ASC"
        return db.query(sql)

    def get_match_list(self, world_id):
        sql = "SELECT DISTINCT zone_id FROM death_event WHERE zone_id > 65535 AND world_id = ?"
        return db.query(sql, [world_id])

    def get_vehicle_kills(self, zone_id):
        sql = "SELECT COUNT(1) AS num, attacker_outfit.alias AS attacker_outfit, " \
              "defender_outfit.alias AS defender_outfit, defender_vehicle_info.name AS vehicle_name " \
              "FROM vehicle_destroy_event e " \
              "LEFT JOIN character_info defender ON e.character_id = defender.character_id " \
              "LEFT JOIN outfit_info defender_outfit ON defender.outfit_id = defender_outfit.outfit_id " \
              "LEFT JOIN character_info attacker ON e.attacker_character_id = attacker.character_id " \
              "LEFT JOIN outfit_info attacker_outfit ON attacker.outfit_id = attacker_outfit.outfit_id " \
              "JOIN vehicle_info defender_vehicle_info ON e.character_vehicle_id = defender_vehicle_info.vehicle_id " \
              "WHERE e.zone_id = ? " \
              "GROUP BY attacker_outfit.alias, defender_outfit.alias, defender_vehicle_info.name " \
              "ORDER BY defender_vehicle_info.name DESC"
        return db.query(sql, [zone_id])

    def get_kill_events(self, zone_id):
        sql = "SELECT COUNT(1) AS num, SUM(is_headshot) AS num_headshot, attacker_faction.alias AS attacker_faction, defender_faction.alias AS defender_faction " \
              "FROM death_event e " \
              "LEFT JOIN zone_info ON e.zone_id = zone_info.zone_id " \
              "LEFT JOIN loadout_info attacker ON e.attacker_loadout_id = attacker.loadout_id " \
              "LEFT JOIN faction_info attacker_faction ON attacker.faction_id = attacker_faction.faction_id " \
              "LEFT JOIN loadout_info defender ON e.character_loadout_id = defender.loadout_id " \
              "LEFT JOIN faction_info defender_faction ON defender.faction_id = defender_faction.faction_id " \
              "WHERE e.zone_id = ? " \
              "GROUP BY attacker_faction.alias, defender_faction.alias"
        return db.query(sql, [zone_id])

    def get_zone_info(self):
        return db.query("SELECT zone_id, name FROM zone_info")

    def get_resist_type_list(self, version_id):
        return db.query("SELECT damage_type_id, name FROM damage_type WHERE version_id = ? ORDER BY damage_type_id ASC", [version_id])

    def get(self, version_id, resist_type_id):
        sql = """
            SELECT weapon_id, name, max_damage, min_damage, indirect_damage, damage_type_id, indirect_damage_type_id, is_flak 
            FROM weapon
            WHERE version_id = ?
            AND (damage_type_id = ? OR indirect_damage_type_id = ?)
            ORDER BY name ASC
        """

        return db.query(sql, [version_id, resist_type_id, resist_type_id])

    def get_version_list(self):
        return db.query("SELECT id, name FROM version ORDER BY order ASC")

    def get_weapon_list(self):
        return db.query("SELECT DISTINCT weapon_id, name FROM weapon ORDER BY weapon_id ASC")

    def get_target_list(self):
        return db.query("SELECT DISTINCT t.target_id, t.name FROM target t "
                        "JOIN damage_resistance r ON (t.target_id = r.target_id AND t.version_id = r.version_id) "
                        "ORDER BY t.target_id ASC")

    def get_direction_list(self):
        return db.query("SELECT id, name FROM attack_direction ORDER BY id")

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

        rows = db.query(sql, params)

        data = []
        for row in rows:
            data.append(row)

        return data
