import os
import logging
from typing import Optional, Dict, Any, List
import mysql.connector
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime

# Load environment variables
load_dotenv()

logger = logging.getLogger("DB_Connector")

class OptEazyDB:
    """
    Unified Database Manager for MySQL (Analytical History) 
    and MongoDB (Raw Snapshot Storage).
    """
    def __init__(self):
        # MySQL Config from environment
        self.mysql_config = {
            "host": os.getenv("MYSQL_HOST", "localhost"),
            "port": int(os.getenv("MYSQL_PORT", 3306)),
            "user": os.getenv("MYSQL_USER", "root"),
            "password": os.getenv("MYSQL_PASS", ""),
            "database": os.getenv("MYSQL_DB", "opteazy"),
        }
        
        # MongoDB Config from environment
        self.mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
        
        self._mysql_conn = None
        self._mongo_client = None

    def connect_mysql(self) -> bool:
        """Attempts to connect to MySQL."""
        try:
            if self._mysql_conn and self._mysql_conn.is_connected():
                return True
            
            self._mysql_conn = mysql.connector.connect(**self.mysql_config)
            logger.info("Successfully connected to MySQL")
            return True
        except Exception as e:
            logger.error(f"MySQL Connection Failed: {e}")
            return False

    def connect_mongo(self) -> bool:
        """Attempts to connect to MongoDB."""
        try:
            self._mongo_client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=2000)
            # Trigger a call to verify connection
            self._mongo_client.admin.command('ping')
            logger.info("Successfully connected to MongoDB")
            return True
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"MongoDB Connection Failed: {e}")
            return False

    def test_all_connections(self) -> Dict[str, bool]:
        """Diagnostic method to check both DB status."""
        return {
            "MySQL": self.connect_mysql(),
            "MongoDB": self.connect_mongo()
        }

    def create_tables(self):
        """Ensures that required MySQL tables exist."""
        if not self.connect_mysql():
            return
        cursor = self._mysql_conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evolution_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                expiry VARCHAR(50),
                timestamp DATETIME,
                spot FLOAT,
                pcr_1_percent FLOAT,
                pcr_2_percent FLOAT,
                pcr_3_percent FLOAT,
                pcr_4_percent FLOAT,
                pcr_5_percent FLOAT,
                pcr_overall FLOAT,
                major_support_strike FLOAT,
                major_resistance_strike FLOAT,
                immediate_support_strike FLOAT,
                immediate_resistance_strike FLOAT,
                UNIQUE KEY unique_record (expiry, timestamp)
            )
        """)
        self._mysql_conn.commit()
        cursor.close()

    def save_analysis_record(self, record: Dict[str, Any]):
        """Saves analysis data to MySQL."""
        if not self.connect_mysql():
            return False
        
        try:
            self.create_tables()
            cursor = self._mysql_conn.cursor()
            
            sql = """
                INSERT INTO evolution_history 
                (expiry, timestamp, spot, pcr_1_percent, pcr_2_percent, pcr_3_percent, pcr_4_percent, pcr_5_percent, pcr_overall, major_support_strike, major_resistance_strike, immediate_support_strike, immediate_resistance_strike)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                spot=VALUES(spot), pcr_1_percent=VALUES(pcr_1_percent), pcr_2_percent=VALUES(pcr_2_percent), 
                pcr_3_percent=VALUES(pcr_3_percent), pcr_4_percent=VALUES(pcr_4_percent), pcr_5_percent=VALUES(pcr_5_percent), 
                pcr_overall=VALUES(pcr_overall), major_support_strike=VALUES(major_support_strike), 
                major_resistance_strike=VALUES(major_resistance_strike), 
                immediate_support_strike=VALUES(immediate_support_strike), 
                immediate_resistance_strike=VALUES(immediate_resistance_strike)
            """
            
            ts = record.get("Timestamp")
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            
            val = (
                record.get("expiry"),
                ts,
                record.get("Spot"),
                record.get("PCR Ranged (1%)"),
                record.get("PCR Ranged (2%)"),
                record.get("PCR Ranged (3%)"),
                record.get("PCR Ranged (4%)"),
                record.get("PCR Ranged (5%)"),
                record.get("PCR Overall"),
                record.get("Major Support"),
                record.get("Major Resistance"),
                record.get("Immediate Support"),
                record.get("Immediate Resistance")
            )
            
            cursor.execute(sql, val)
            self._mysql_conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error(f"Failed to save record to MySQL: {e}")
            return False

    def save_raw_snapshot(self, data: Dict[str, Any], expiry: str, timestamp: str):
        """Saves raw snapshot metadata to MongoDB."""
        if not self.connect_mongo():
            return False
        try:
            db = self._mongo_client["opteazy_raw"]
            collection = db[expiry.replace("-", "_")]
            
            if collection.find_one({"internal_ts": timestamp}):
                return True
                
            data["internal_ts"] = timestamp
            collection.insert_one(data)
            return True
        except Exception as e:
            logger.error(f"Failed to save snapshot to MongoDB: {e}")
            return False

    def create_indicator_table(self, table_name: str):
        """Ensures that a daily MySQL table for market indicators exists."""
        if not self.connect_mysql():
            return
        cursor = self._mysql_conn.cursor()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                timestamp DATETIME,
                usd_inr FLOAT,
                wti_crude FLOAT,
                brent_crude FLOAT,
                UNIQUE KEY unique_record (timestamp)
            )
        """)
        self._mysql_conn.commit()
        cursor.close()

    def save_market_indicators(self, data: Dict[str, Any], date_str: str):
        """Saves indicator data to both MySQL and MongoDB daily collections."""
        # Normalize date_str to DD_MM_YYYY format for table names
        normalized_date = date_str.replace("-", "_")
        table_name = f"market_indicators_{normalized_date}"
        
        # 1. MySQL Storage (Efficiency)
        if self.connect_mysql():
            try:
                self.create_indicator_table(table_name)
                cursor = self._mysql_conn.cursor()
                sql = f"INSERT IGNORE INTO {table_name} (timestamp, usd_inr, wti_crude, brent_crude) VALUES (%s, %s, %s, %s)"
                
                ts = data.get("timestamp")
                if isinstance(ts, str):
                    ts = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                
                val = (ts, data.get("USD_INR"), data.get("WTI_Crude"), data.get("Brent_Crude"))
                cursor.execute(sql, val)
                self._mysql_conn.commit()
                cursor.close()
            except Exception as e:
                logger.error(f"Failed to save indicator record to MySQL: {e}")

        # 2. MongoDB Storage (Detailed Dump)
        if self.connect_mongo():
            try:
                db = self._mongo_client["opteazy_raw"]
                collection = db[table_name]
                
                ts = data.get("timestamp")
                if not collection.find_one({"timestamp": ts}):
                    collection.insert_one(data)
            except Exception as e:
                logger.error(f"Failed to save indicator dump to MongoDB: {e}")

    def query_market_indicators(self, date_str: str) -> pd.DataFrame:
        """Retrieves indicator data for a specific date from MySQL."""
        if not self.connect_mysql():
            return pd.DataFrame()
            
        normalized_date = date_str.replace("-", "_")
        table_name = f"market_indicators_{normalized_date}"
        
        try:
            # Check if table exists
            cursor = self._mysql_conn.cursor()
            cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
            if not cursor.fetchone():
                return pd.DataFrame()
                
            query = f"SELECT * FROM {table_name} ORDER BY timestamp ASC"
            df = pd.read_sql(query, self._mysql_conn)
            cursor.close()
            return df
        except Exception as e:
            logger.error(f"Failed to query indicators: {e}")
            return pd.DataFrame()

    def query_evolution_data(self, expiry: str) -> pd.DataFrame:
        """Queries historical analysis data for a specific expiry from MySQL."""
        if not self.connect_mysql():
            return pd.DataFrame()
            
        try:
            self.create_tables()
            query = """
                SELECT timestamp as Timestamp, spot as Spot, 
                pcr_1_percent as 'PCR Ranged (1%)', 
                pcr_2_percent as 'PCR Ranged (2%)', 
                pcr_3_percent as 'PCR Ranged (3%)', 
                pcr_4_percent as 'PCR Ranged (4%)', 
                pcr_5_percent as 'PCR Ranged (5%)', 
                pcr_overall as 'PCR Overall',
                major_support_strike as 'Major Support', 
                major_resistance_strike as 'Major Resistance', 
                immediate_support_strike as 'Immediate Support', 
                immediate_resistance_strike as 'Immediate Resistance'
                FROM evolution_history 
                WHERE expiry = %s 
                ORDER BY timestamp ASC
            """
            cursor = self._mysql_conn.cursor(dictionary=True)
            cursor.execute(query, (expiry,))
            rows = cursor.fetchall()
            df = pd.DataFrame(rows)
            cursor.close()
            return df
        except Exception as e:
            logger.error(f"Failed to query evolution data: {e}")
            return pd.DataFrame()

    def reset_databases(self):
        """Wipes all data from both MySQL and MongoDB."""
        if self.connect_mysql():
            cursor = self._mysql_conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS evolution_history")
            self._mysql_conn.commit()
            self.create_tables()
            cursor.close()
            logger.info("MySQL evolution_history table reset.")

        if self.connect_mongo():
            db = self._mongo_client["opteazy_raw"]
            for coll_name in db.list_collection_names():
                db.drop_collection(coll_name)
            logger.info("MongoDB opteazy_raw database reset.")

    def close(self):
        """Cleanup connections."""
        if self._mysql_conn and self._mysql_conn.is_connected():
            self._mysql_conn.close()
        if self._mongo_client:
            self._mongo_client.close()
