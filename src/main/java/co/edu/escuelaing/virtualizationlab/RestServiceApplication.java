package co.edu.escuelaing.virtualizationlab;

import java.util.Map;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Application entry point.
 *
 * <p>The listening port is read from the {@code PORT} environment variable so
 * the same artifact can run unchanged on a laptop, inside a container or on an
 * EC2 instance. When {@code PORT} is not set, the server listens on 6000.
 */
@SpringBootApplication
public class RestServiceApplication {

    static final String PORT_VARIABLE = "PORT";
    static final String DEFAULT_PORT = "6000";

    public static void main(String[] args) {
        SpringApplication application =
                new SpringApplication(RestServiceApplication.class);

        application.setDefaultProperties(
                Map.of("server.port", resolvePort(System.getenv())));

        application.run(args);
    }

    static String resolvePort(Map<String, String> environment) {
        String port = environment.get(PORT_VARIABLE);
        return (port == null || port.isBlank()) ? DEFAULT_PORT : port.trim();
    }
}
