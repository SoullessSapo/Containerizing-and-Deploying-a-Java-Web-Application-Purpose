package co.edu.escuelaing.virtualizationlab;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.util.Map;
import org.junit.jupiter.api.Test;

class RestServiceApplicationTest {

    @Test
    void usesThePortEnvironmentVariableWhenPresent() {
        assertEquals("9000", RestServiceApplication.resolvePort(Map.of("PORT", "9000")));
    }

    @Test
    void defaultsTo6000WhenPortIsMissing() {
        assertEquals("6000", RestServiceApplication.resolvePort(Map.of()));
    }

    @Test
    void defaultsTo6000WhenPortIsBlank() {
        assertEquals("6000", RestServiceApplication.resolvePort(Map.of("PORT", "  ")));
    }
}
