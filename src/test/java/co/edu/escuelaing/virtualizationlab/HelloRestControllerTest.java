package co.edu.escuelaing.virtualizationlab;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.test.web.servlet.MockMvc;

@WebMvcTest(HelloRestController.class)
class HelloRestControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void greetsTheGivenName() throws Exception {
        mockMvc.perform(get("/greeting").param("name", "Pedro"))
                .andExpect(status().isOk())
                .andExpect(content().string("Hello, Pedro!"));
    }

    @Test
    void greetsTheWorldWhenNoNameIsGiven() throws Exception {
        mockMvc.perform(get("/greeting"))
                .andExpect(status().isOk())
                .andExpect(content().string("Hello, World!"));
    }
}
