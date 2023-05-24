lazy_static::lazy_static! {
    static ref DEFAULT_BAUD_RATE: u32 = 9600;
}

#[derive(serde::Deserialize, Debug, PartialEq, Clone)]
pub struct AprsSerial {
    #[serde(default = "first_available_port")]
    pub port: String,
    #[serde(default = "default_baud_rate")]
    pub baud_rate: u32,
    #[serde(skip)]
    pub callsigns: Option<Vec<String>>,
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
                            message: format!("error connecting to port {:?} - {:}", &name, error,),
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
                return Err(super::super::ConnectionError::FailedToEstablish {
                    connection: format!("{:}@{:}", self.port, self.baud_rate),
                    message: error.to_string(),
                });
            }
        };

        let mut buffer = Vec::<u8>::new();
        match connection.read_to_end(&mut buffer) {
            Ok(_) => Ok(buffer
                .split(|a| a == &b'\n')
                .filter_map(|line| {
                    match crate::location::BalloonLocation::from_aprs_frame(line, None) {
                        Ok(location) => {
                            if let Some(callsigns) = &self.callsigns {
                                if !callsigns.contains(
                                    &location
                                        .data
                                        .aprs_packet
                                        .to_owned()
                                        .unwrap()
                                        .from
                                        .call()
                                        .to_string(),
                                ) {
                                    return None;
                                }
                            }
                            Some(location)
                        }
                        Err(_) => None,
                    }
                })
                .collect()),
            Err(error) => Err(crate::connection::ConnectionError::ReadFailure {
                connection: format!("{:}@{:}", self.port, self.baud_rate),
                message: error.to_string(),
            }),
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

fn default_baud_rate() -> u32 {
    *DEFAULT_BAUD_RATE
}
