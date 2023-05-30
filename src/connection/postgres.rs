use chrono::TimeZone;

#[derive(serde::Deserialize, Debug, PartialEq, Clone)]
pub struct DatabaseCredentials {
    pub hostname: String,
    pub port: u32,
    pub database: String,
    pub table: String,
    pub username: String,
    pub password: String,
    pub tunnel: Option<SshCredentials>,
}
impl DatabaseCredentials {
    pub fn new(
        hostname: String,
        port: Option<u32>,
        database: Option<String>,
        table: String,
        username: String,
        password: String,
        tunnel: Option<SshCredentials>,
    ) -> Self {
        Self {
            hostname,
            port: match port {
                Some(port) => port,
                None => 5432,
            },
            database: match database {
                Some(database) => database,
                None => username.to_owned(),
            },
            table,
            username,
            password,
            tunnel,
        }
    }

    pub fn client(&self) -> postgres::Client {
        postgres::Client::connect(
            &format!(
                "host={:} port={:} dbname={:} user={:} password={:}",
                self.hostname, self.port, self.database, self.username, self.password,
            ),
            postgres::NoTls,
        )
        .unwrap()
    }
}

pub struct PacketDatabase {
    credentials: DatabaseCredentials,
    client: postgres::Client,
}

impl Clone for PacketDatabase {
    fn clone(&self) -> Self {
        Self {
            credentials: self.credentials.clone(),
            client: self.credentials.client(),
        }
    }
}

impl std::fmt::Debug for PacketDatabase {
    fn fmt(&self, fmt: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(fmt, "{:?}", self.credentials)
    }
}

impl Default for PacketDatabase {
    fn default() -> Self {
        Self::new(
            String::from("localhost"),
            None,
            None,
            String::from("default_table"),
            String::from("postgres"),
            String::from(""),
            None,
        )
    }
}
impl PacketDatabase {
    pub fn new(
        hostname: String,
        port: Option<u32>,
        database: Option<String>,
        table: String,
        username: String,
        password: String,
        tunnel: Option<SshCredentials>,
    ) -> Self {
        let credentials =
            DatabaseCredentials::new(hostname, port, database, table, username, password, tunnel);
        Self::from_credentials(&credentials)
    }

    pub fn from_credentials(credentials: &DatabaseCredentials) -> Self {
        Self {
            credentials: credentials.to_owned(),
            client: credentials.client(),
        }
    }

    pub fn table_exists(&mut self, table: &String) -> bool {
        self.client
            .query_one(
                "SELECT EXISTS(SELECT 1 FROM pg_class WHERE relname=%s);",
                &[table],
            )
            .unwrap()
            .get(0)
    }

    pub fn retrieve_locations_from_database(
        &mut self,
    ) -> Result<Vec<crate::location::BalloonLocation>, crate::connection::ConnectionError> {
        let mut locations: Vec<crate::location::BalloonLocation> = vec![];

        self.client
            .batch_execute(&format!(
                "
                    CREATE TABLE {:} (
                        time    TIMESTAMP, 
                        x       REAL, 
                        y       REAL, 
                        z       REAL, 
                        source  VARCHAR, 
                        point   GEOMETRY, 
                        PRIMARY KEY(time)
                    )
                ",
                self.credentials.table
            ))
            .unwrap();

        for row in self
            .client
            .query(
                &format!("SELECT time, x, y, z FROM {:}", self.credentials.table),
                &[],
            )
            .unwrap()
        {
            locations.push(crate::location::BalloonLocation {
                location: crate::location::Location {
                    time: chrono::Local.timestamp_opt(row.get(0), 0).unwrap(),
                    coord: geo::coord! { x: row.get(1), y: row.get(2) },
                    altitude: Some(row.get(3)),
                },
                data: crate::location::BalloonData::new(
                    None,
                    None,
                    None,
                    None,
                    crate::location::LocationSource::Database(format!(
                        "{:}:{:}",
                        self.credentials.hostname, self.credentials.port,
                    )),
                ),
            });
        }

        Ok(locations)
    }

    pub fn insert(&self) {
        // TODO
    }
}

fn default_port() -> u32 {
    22
}

#[derive(serde::Deserialize, Debug, PartialEq, Clone)]
pub struct SshCredentials {
    pub hostname: String,
    #[serde(default = "default_port")]
    pub port: u32,
    pub username: String,
    pub password: String,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    #[ignore]
    fn test_database() {
        if let Ok(hostname) = std::env::var("POSTGRES_HOSTNAME") {
            let port = match std::env::var("POSTGRES_PORT") {
                Ok(port) => Some(port.parse::<u32>().unwrap()),
                Err(_) => None,
            };
            let database = match std::env::var("POSTGRES_DATABASE") {
                Ok(database) => Some(database),
                Err(_) => None,
            };
            let username = std::env::var("POSTGRES_USERNAME").unwrap();
            let password = std::env::var("POSTGRES_PASSWORD").unwrap();

            let tunnel = match std::env::var("SSH_HOSTNAME") {
                Ok(hostname) => Some(SshCredentials {
                    hostname,
                    port: match std::env::var("SSH_PORT") {
                        Ok(port) => port.parse::<u32>().unwrap(),
                        Err(_) => 22,
                    },
                    username: std::env::var("SSH_USERNAME").unwrap(),
                    password: std::env::var("SSH_PASSWORD").unwrap(),
                }),
                Err(_) => None,
            };

            let mut database = crate::connection::postgres::PacketDatabase::new(
                hostname,
                port,
                database,
                String::from("test_table"),
                username,
                password,
                tunnel,
            );

            let table_name = String::from("test_table");

            database.table_exists(&table_name);
            database
                .client
                .execute("DROP TABLE table;", &[&table_name])
                .unwrap();

            let packet_1 = crate::location::BalloonLocation::from_aprs_frame(
        "W3EAX-13>APRS,N3KTX-10*,WIDE1,WIDE2-1,qAR,N3TJJ-11:!/:J..:sh'O   /A=053614|!g|  /W3EAX,313,0,21'C,nearspace.umd.edu".as_bytes(),
        Some(chrono::Local.with_ymd_and_hms(2019, 2, 3, 14, 36, 16).unwrap()),
    ).unwrap();
            let packet_2 = crate::location::BalloonLocation::from_aprs_frame(
        "W3EAX-13>APRS,WIDE1-1,WIDE2-1,qAR,W4TTU:!/:JAe:tn8O   /A=046255|!i|  /W3EAX,322,0,20'C,nearspace.umd.edu".as_bytes(),
        Some(chrono::Local.with_ymd_and_hms(2019, 2, 3, 14, 38, 23).unwrap()),
    ).unwrap();
            let packet_3 = crate::location::BalloonLocation::from_aprs_frame(
        "W3EAX-13>APRS,KC3FIT-1,WIDE1*,WIDE2-1,qAR,KC3AWP-10:!/:JL2:u4wO   /A=043080|!j|  /W3EAX,326,0,20'C,nearspace.umd.edu".as_bytes(),
        Some(chrono::Local.with_ymd_and_hms(2019, 2, 3, 14, 39, 28).unwrap()),
    ).unwrap();

            let input_packets = vec![packet_1, packet_2, packet_3];

            // database.insert(input_packets, table_name);

            // assert_eq!(
            //     packet_1,
            //     database.get(
            //         packet_1.time,
            //         packet_1.data.aprs_packet.unwrap().from.call()
            //     )
            // );

            let mut connection = super::super::Connection::PacketDatabase(database);
            let packets = connection.retrieve_locations().unwrap();

            // database.table_exists(&table_name);
            // database.client.execute("DROP TABLE table;", &[&table_name]);

            assert!(!packets.is_empty());

            for index in 0..packets.len() {
                assert_eq!(
                    packets.get(index).unwrap(),
                    input_packets.get(index).unwrap()
                )
            }
        } else {
            panic!("database credentials not set in environment variables");
        }
    }
}
