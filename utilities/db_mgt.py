import mysql
from mysql.connector import errorcode


class sst_db:
    def __init__(self, db):
        self.db = db

    def __enter__(self):
        try:
            self.cnx = mysql.connector.connect(user='XXX', password='yyyyyyyy',
                                               host='127.0.0.1',
                                               database=self.db,
                                               use_unicode=True)
            return self.cnx
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                print("Something is wrong with your user name or password")
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                print("Database does not exist")
            else:
                print(err)

    def __exit__(self, x, y, z):
        self.cnx.close()
