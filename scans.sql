PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE scan_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        floor TEXT,
        location TEXT,
        timestamp TEXT
    );
INSERT INTO scan_logs VALUES(1,'Ua4f8171df7f9424622a3050f49076db7','1F','機械系館1','2025/02/07 17:53:08');
INSERT INTO scan_logs VALUES(2,'Ua4f8171df7f9424622a3050f49076db7','1F','機械系館1','2025/02/07 17:54:49');
INSERT INTO scan_logs VALUES(3,'Ua4f8171df7f9424622a3050f49076db7','2F','機械系館1','2025/02/08 11:06:23');
INSERT INTO scan_logs VALUES(4,'Ua4f8171df7f9424622a3050f49076db7','1F','機械系館1','2025/02/08 11:06:45');
INSERT INTO scan_logs VALUES(5,'Ua4f8171df7f9424622a3050f49076db7','3F','機械系館1','2025/02/08 11:07:03');
INSERT INTO scan_logs VALUES(6,'Ua4f8171df7f9424622a3050f49076db7','5F','機械系館1','2025/02/08 11:07:18');
INSERT INTO scan_logs VALUES(7,'Ua4f8171df7f9424622a3050f49076db7','1F','機械系館1','2025/02/09 17:39:30');
INSERT INTO scan_logs VALUES(8,'Ua4f8171df7f9424622a3050f49076db7','1F','機械系館1','2025/02/09 17:39:52');
INSERT INTO scan_logs VALUES(9,'Ua4f8171df7f9424622a3050f49076db7','2F','機械系館1','2025/02/09 17:48:26');
INSERT INTO scan_logs VALUES(10,'Ua4f8171df7f9424622a3050f49076db7','2F','機械系館1','2025/02/09 17:48:53');
INSERT INTO scan_logs VALUES(11,'Ua4f8171df7f9424622a3050f49076db7','2F','機械系館1','2025/02/09 18:25:52');
INSERT INTO scan_logs VALUES(12,'Ua4f8171df7f9424622a3050f49076db7','2F','機械系館1','2025/02/09 18:28:15');
INSERT INTO scan_logs VALUES(13,'Ua4f8171df7f9424622a3050f49076db7','2F','機械系館1''','2025/02/09 18:29:24');
INSERT INTO scan_logs VALUES(14,'Ua4f8171df7f9424622a3050f49076db7','2F','機械系館1''','2025/02/09 18:29:44');
INSERT INTO scan_logs VALUES(15,'Ua4f8171df7f9424622a3050f49076db7','2F','機械系館1','2025/02/09 23:26:37');
INSERT INTO scan_logs VALUES(16,'Ubf4585d9dbf2af522d04766677e77c23','1F','機械系館1','2025/02/09 23:28:54');
INSERT INTO scan_logs VALUES(17,'Ua4f8171df7f9424622a3050f49076db7','5F','機械系館1','2025/02/09 23:30:41');
INSERT INTO scan_logs VALUES(18,'Ubf4585d9dbf2af522d04766677e77c23','5F','機械系館1','2025/02/09 23:30:58');
INSERT INTO scan_logs VALUES(19,'Ubf4585d9dbf2af522d04766677e77c23','5F','機械系館1','2025/02/09 23:34:22');
INSERT INTO scan_logs VALUES(20,'Ubf4585d9dbf2af522d04766677e77c23','1F','機械系館1','2025/02/09 23:35:04');
INSERT INTO scan_logs VALUES(21,'Ubf4585d9dbf2af522d04766677e77c23','1F','機械系館1','2025/02/09 23:35:35');
INSERT INTO scan_logs VALUES(22,'Ubf4585d9dbf2af522d04766677e77c23','1F','機械系館1','2025/02/09 23:36:35');
INSERT INTO scan_logs VALUES(23,'Ubf4585d9dbf2af522d04766677e77c23','1F','機械系館1','2025/02/09 23:37:08');
INSERT INTO scan_logs VALUES(24,'Ubf4585d9dbf2af522d04766677e77c23','1F','機械系館1','2025/02/09 23:37:28');
INSERT INTO scan_logs VALUES(25,'Ubf4585d9dbf2af522d04766677e77c23','1F','機械系館1','2025/02/09 23:37:46');
INSERT INTO scan_logs VALUES(26,'Ubf4585d9dbf2af522d04766677e77c23','1F','機械系館1','2025/02/09 23:38:16');
INSERT INTO scan_logs VALUES(27,'Ubf4585d9dbf2af522d04766677e77c23','1F','機械系館1','2025/02/09 23:38:37');
INSERT INTO scan_logs VALUES(28,'Ua4f8171df7f9424622a3050f49076db7','1F','機械系館1','2025/02/11 14:28:21');
INSERT INTO scan_logs VALUES(29,'Ub94d3f0275b8b3b4af28a551d39b2979','1F','機械系館1','2025/02/12 10:13:49');
INSERT INTO scan_logs VALUES(30,'Ub94d3f0275b8b3b4af28a551d39b2979','1F','機械系館1','2025/02/12 10:17:08');
CREATE TABLE all_user_points (
        user_id TEXT PRIMARY KEY,
        points INTEGER DEFAULT 0,
        level INTEGER DEFAULT 0,
        points_to_next_level INTEGER DEFAULT 0,
        ranking INTEGER DEFAULT NULL
    );
INSERT INTO all_user_points VALUES('Ua4f8171df7f9424622a3050f49076db7',9,1,41,2);
INSERT INTO all_user_points VALUES('Ubf4585d9dbf2af522d04766677e77c23',11,1,39,1);
INSERT INTO all_user_points VALUES('Ub94d3f0275b8b3b4af28a551d39b2979',2,1,48,3);
CREATE TABLE user_settings (
        user_id TEXT PRIMARY KEY,
        location_consent INTEGER DEFAULT 0,
        language TEXT DEFAULT 'English'
    );
INSERT INTO user_settings VALUES('Ub94d3f0275b8b3b4af28a551d39b2979',1,'English');
INSERT INTO user_settings VALUES('Ua4f8171df7f9424622a3050f49076db7',0,'Chinese');
CREATE TABLE feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        report TEXT,
        timestamp TEXT
    );
INSERT INTO feedback VALUES(1,'Ua4f8171df7f9424622a3050f49076db7','First','2025-02-12 12:46:27');
INSERT INTO feedback VALUES(2,'Ua4f8171df7f9424622a3050f49076db7','測試','2025-02-12 12:46:52');
DELETE FROM sqlite_sequence;
INSERT INTO sqlite_sequence VALUES('scan_logs',30);
INSERT INTO sqlite_sequence VALUES('feedback',2);
COMMIT;
