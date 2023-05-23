lazy_static::lazy_static! {
    static ref DEFAULT_BAUD_RATE: u32 = 9600;
}

fn first_available_port() -> String {
    // TODO iterate over baud rates
    match serialport::available_ports() {
        Ok(available_ports) => {
            for available_port in available_ports {
                let connection_attempt =
                    serialport::new(available_port.port_name, *DEFAULT_BAUD_RATE).open();
                match connection_attempt {
                    Ok(successful) => {
                        return successful.name().unwrap();
                    }
                    Err(error) => {
                        panic!("{:}", error);
                    }
                }
            }
            panic!("{:}", "ports list is empty when it should not be");
        }
        Err(error) => {
            panic!("{:}", error);
        }
    }
}

#[derive(serde::Deserialize, Debug)]
pub struct AprsSerial {
    #[serde(default = "first_available_port")]
    pub port: String,
    pub baud_rate: u32,
    #[serde(skip)]
    callsigns: Option<Vec<String>>,
}

impl AprsSerial {
    pub fn new(
        port: Option<String>,
        baud_rate: Option<u32>,
        callsigns: Option<Vec<String>>,
    ) -> Result<Self, crate::connection::ConnectionError> {
        let baud = baud_rate.unwrap_or(*DEFAULT_BAUD_RATE);
        let mut port_name: Option<String> = None;
        match port {
            Some(name) => {
                port_name = match serialport::new(&name, baud).open() {
                    Ok(port) => port.name(),
                    Err(error) => {
                        return Err(crate::connection::ConnectionError::FailedToEstablish {
                            connection: "serial".to_string(),
                            message: format!(
                                "error connecting to port {:?} at baud {:?} - {:}",
                                &name,
                                baud_rate.unwrap(),
                                error,
                            ),
                        });
                    }
                };
            }
            None => {
                let available_ports = match serialport::available_ports() {
                    Ok(ports) => ports,
                    Err(error) => {
                        return Err(crate::connection::ConnectionError::FailedToEstablish {
                            connection: "serial".to_string(),
                            message: error.to_string(),
                        })
                    }
                };

                // return the next available port
                for port in available_ports {
                    let connection_attempt = serialport::new(port.port_name, baud).open();
                    match connection_attempt {
                        Ok(successful) => {
                            port_name = successful.name();
                            break;
                        }
                        Err(_) => {
                            continue;
                        }
                    }
                }
            }
        }

        if let Some(port_name) = port_name {
            Ok(Self {
                port: port_name,
                baud_rate: baud,
                callsigns,
            })
        } else {
            Err(crate::connection::ConnectionError::FailedToEstablish {
                connection: "serial".to_string(),
                message: "no open ports".to_string(),
            })
        }
    }

    pub fn read_aprs_from_serial(
        &self,
    ) -> Result<Vec<crate::location::BalloonLocation>, crate::connection::ConnectionError> {
        let mut connection = match serialport::new(&self.port, self.baud_rate).open() {
            Ok(connection) => connection,
            Err(error) => {
                return Err(super::ConnectionError::FailedToEstablish {
                    connection: "serial".to_string(),
                    message: error.to_string(),
                });
            }
        };

        let mut buffer = Vec::<u8>::new();
        match connection.read_to_end(&mut buffer) {
            Ok(_) => {
                let mut locations: Vec<crate::location::BalloonLocation> = vec![];
                for line in buffer.split(|a| a == &b'\n') {
                    let location =
                        crate::location::BalloonLocation::from_aprs_frame(line, None).unwrap();
                    if let Some(callsigns) = &self.callsigns {
                        if let Some(aprs_packet) = &location.data.aprs_packet {
                            if !callsigns.contains(&aprs_packet.from.call().to_string()) {
                                continue;
                            }
                        }
                    }
                    locations.push(location);
                }
                Ok(locations)
            }
            Err(error) => panic!("{:?}", error),
        }
    }
}

impl Default for AprsSerial {
    fn default() -> Self {
        match Self::new(None, None, None) {
            Ok(connection) => connection,
            Err(error) => panic!("{:}", error),
        }
    }
}
