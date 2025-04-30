/**
 * Copyright (C) Bruce MacKinnon, 2025
 */
#include <stdio.h>
#include <stdlib.h>

#include "pico/stdlib.h"
#include "pico/flash.h"
#include "pico/bootrom.h"

#include "hardware/gpio.h"
#include "hardware/i2c.h"
#include "hardware/spi.h"
#include "hardware/sync.h"

#include "kc1fsz-tools/Log.h"
#include "kc1fsz-tools/rp2040/PicoClock.h"
#include "kc1fsz-tools/rp2040/PicoPollTimer.h"
#include "kc1fsz-tools/rp2040/SX1276Driver.h"

#include "kc1fsz-tools/rp2040/SWDDriver.h"
#include "kc1fsz-tools/SWDUtils.h"

#include "main-remote.h"

using namespace kc1fsz;

#define LARGEST_PAYLOAD (120)
#define CLK_PIN (16)
#define DIO_PIN (17)

const uint LED_PIN = 25;

static int int_pin_0 = 0;
static int int_pin_1 = 0;
static volatile bool int_flag_0 = false;
static volatile bool int_flag_1 = false;
static bool local_echo = false;

void gpio_callback(uint gpio, uint32_t events) {
    if (gpio == int_pin_0)
        int_flag_0 = true;
    else if (gpio == int_pin_1)
        int_flag_1 = true;
}

unsigned int convert_ascii_to_bin(const char* ascii_string, uint8_t* bin_string, unsigned int bin_string_len) {

    unsigned int in_ptr = 0;
    unsigned int out_ptr = 0;
    uint8_t last_nibble = 0;
    char c = 0;

    while ((c = ascii_string[in_ptr++]) != 0) {
        if (out_ptr < bin_string_len) {
            // Convert ASCII character to binary nibble
            uint8_t nibble = 0;
            if (c >= '0' && c <= '9') {
                nibble = (int)c - (int)'0';
            }
            else if (c >= 'a' && c <= 'f') {
                nibble = 10 + ((int)c - (int)'a');
            }
            else if (c >= 'A' && c <= 'F') {
                nibble = 10 + ((int)c - (int)'A');
            }
            // Even inputs are combined with accumulator and written to output
            if ((in_ptr & 1) == 0) 
                bin_string[out_ptr++] = (last_nibble << 4) | (nibble & 0b1111);        
            // Even inputs go into accumulator
            last_nibble = nibble;
        }
    }

    return out_ptr;
}

unsigned int convert_bin_to_ascii(const uint8_t* bin_string, unsigned int bin_string_len, 
    char* ascii_string, unsigned int ascii_string_len) {

    unsigned int in_ptr = 0;
    unsigned int out_ptr = 0;
    const char hex_tab[16] = { '0', '1', '2', '3', '4', '5', '6', '7',
                               '8', '9', 'A', 'B', 'C', 'D', 'E', 'F' };

    for (unsigned in_ptr = 0; in_ptr < bin_string_len; in_ptr++) {
        uint8_t high_nibble = (bin_string[in_ptr] >> 4) & 0b1111;
        uint8_t low_nibble = bin_string[in_ptr] & 0b1111;

        // Always leaving space for the null
        if (out_ptr < (ascii_string_len - 1)) 
            ascii_string[out_ptr++] = hex_tab[high_nibble];
        if (out_ptr < (ascii_string_len - 1)) 
            ascii_string[out_ptr++] = hex_tab[low_nibble];
    }   

    ascii_string[out_ptr++] = 0;

    return out_ptr;
}

void process_cmd_local(const char* cmd_line, SX1276Driver& radio) {
    // Split into 4 tokens
    char tokens[4][256] = { { 0 }, { 0 }, { 0 }, { 0 } };
    int cmd_ptr = 0;
    int token = 0;
    int token_ptr = 0;
    while (cmd_line[cmd_ptr] != 0) {
        if (token < 4 && token_ptr < 255) {
            if (cmd_line[cmd_ptr] == ' ') {
                if (token_ptr > 0) {
                    tokens[token++][token_ptr] = 0;
                    token_ptr = 0;
                }
            } 
            else
                tokens[token][token_ptr++] = cmd_line[cmd_ptr];

        }
        cmd_ptr++;
    }
    // Null terminate the last token
    if (token < 4 && token_ptr < 255)
        if (token_ptr > 0)
            tokens[token++][token_ptr] = 0;

    if (strcmp(tokens[0], "send") == 0) {
        uint8_t data[LARGEST_PAYLOAD];
        unsigned int data_len = convert_ascii_to_bin(tokens[1], data, LARGEST_PAYLOAD);
        if (data_len > 0) {
            if (radio.send(data, data_len)) 
                printf("ok\n");
            else 
                printf("fail\n");
        }
        else {
            printf("error\n");
        }
    }
    else if (strcmp(tokens[0], "ping") == 0) {
        printf("ok\n");
    }
    else if (strcmp(tokens[0], "echoon") == 0) {
        local_echo = true;
        printf("ok\n");
    }
    else if (strcmp(tokens[0], "echooff") == 0) {
        local_echo = false;
        printf("ok\n");
    }
    else if (strcmp(tokens[0], "getstatus") == 0) {
        printf("status ");
        if (radio.isSendQueueEmpty())
            printf("y");
        else
            printf("n");
        printf("\n");
    }
    else {
        printf("error\n");
    }
}

int main(int, const char**) {

    stdio_init_all();

    gpio_init(LED_PIN);
    gpio_set_dir(LED_PIN, GPIO_OUT);
      
    gpio_put(LED_PIN, 1);
    sleep_ms(500);
    gpio_put(LED_PIN, 0);
    sleep_ms(500);

    // ----- Radio 0 Hookup 

    int spi_sck_pin_0 = 2;
    int spi_mosi_pin_0 = 3;
    int spi_miso_pin_0 = 4;
    int spi_cs_pin_0 = 5;
    int reset_pin_0 = 6;
    int_pin_0 = 7;

    gpio_init(reset_pin_0);
    gpio_set_dir(reset_pin_0, GPIO_OUT);
    gpio_put(reset_pin_0, 1);

    gpio_init(int_pin_0);
    gpio_set_dir(int_pin_0, GPIO_IN);
    gpio_set_irq_enabled_with_callback(int_pin_0, GPIO_IRQ_EDGE_RISE, true, &gpio_callback);

    // The CS pin is not behaving the way we want, so drive manually
    gpio_init(spi_cs_pin_0);
    gpio_set_dir(spi_cs_pin_0, GPIO_OUT);
    gpio_put(spi_cs_pin_0, 1);

    gpio_set_function(spi_sck_pin_0, GPIO_FUNC_SPI);
    gpio_set_function(spi_mosi_pin_0, GPIO_FUNC_SPI);
    gpio_set_function(spi_miso_pin_0, GPIO_FUNC_SPI);
    spi_init(spi0, 500000);

    // ----- Radio 1 Hookup 

    int spi_sck_pin_1 = 10;
    int spi_mosi_pin_1 = 11;
    int spi_miso_pin_1 = 12;
    int spi_cs_pin_1 = 13;
    int reset_pin_1 = 14;
    int_pin_1 = 15;

    gpio_init(reset_pin_1);
    gpio_set_dir(reset_pin_1, GPIO_OUT);
    gpio_put(reset_pin_1, 1);

    gpio_init(int_pin_1);
    gpio_set_dir(int_pin_1, GPIO_IN);
    // First irq installs callback for all
    gpio_set_irq_enabled(int_pin_1, GPIO_IRQ_EDGE_RISE, true);

    // The CS pin is not behaving the way we want, so drive manually
    gpio_init(spi_cs_pin_1);
    gpio_set_dir(spi_cs_pin_1, GPIO_OUT);
    gpio_put(spi_cs_pin_1, 1);

    gpio_set_function(spi_sck_pin_1, GPIO_FUNC_SPI);
    gpio_set_function(spi_mosi_pin_1, GPIO_FUNC_SPI);
    gpio_set_function(spi_miso_pin_1, GPIO_FUNC_SPI);
    spi_init(spi1, 500000);

    // ----- SWD Hookup -----
    gpio_init(CLK_PIN);
    gpio_set_dir(CLK_PIN, GPIO_OUT);        
    gpio_put(CLK_PIN, 0);
    gpio_init(DIO_PIN);
    gpio_set_dir(DIO_PIN, GPIO_OUT);        
    gpio_put(DIO_PIN, 0);
    SWDDriver swd(CLK_PIN, DIO_PIN);

    PicoClock clock;
    PicoPollTimer radio_poll;
    // Fast poll every 1ms
    radio_poll.setIntervalUs(1000);
    Log log;

    log.info("Remote Probe (Local Node)");

    SX1276Driver radio_0(log, clock, reset_pin_0, spi_cs_pin_0, spi0);
    SX1276Driver radio_1(log, clock, reset_pin_1, spi_cs_pin_1, spi1);

    char cmd_line[256] = { 0 };
    int cmd_line_len = 0;

    while (true) {        

        // Look for interrupt activity and notify the radios
        uint32_t int_state = save_and_disable_interrupts();
        if (int_flag_0) {
            radio_0.event_int();
            int_flag_0 = false;
        }
        if (int_flag_1) {
            radio_1.event_int();
            int_flag_1 = false;
        }        
        restore_interrupts(int_state);

        // Fast poll
        radio_0.event_poll();
        radio_1.event_poll();

        // Slow poll
        if (radio_poll.poll()) {
            radio_0.event_tick();
            radio_1.event_tick();
        }

        // ----- Handle radio receive activity -----

        uint8_t buf[LARGEST_PAYLOAD];
        unsigned int buf_len = LARGEST_PAYLOAD;
        short rssi = 0;

        if (radio_0.popReceiveIfNotEmpty(&rssi, buf, &buf_len)) {
            //log.info("Radio 0 got %d", buf_len);
            char ascii_buf[LARGEST_PAYLOAD * 2 + 1];
            int ascii_buf_len = convert_bin_to_ascii(buf, buf_len, 
                ascii_buf, LARGEST_PAYLOAD * 2 + 1);
            printf("receive %d %s\n", rssi, ascii_buf);
        }

        // TEMP

        if (radio_1.popReceiveIfNotEmpty(0, buf, &buf_len)) {
            //log.info("Radio 1 got %d %d", buf_len, (int)buf[0]);
            process_cmd_remote(buf, buf_len, log, radio_1, swd);
        }

        // ----- Handle console input activity -----

        int c = stdio_getchar_timeout_us(0);
        if (c != PICO_ERROR_TIMEOUT && c != 0) {
            // Look for EOL \n
            if (c == 13) {
                if (local_echo)
                    printf("\n");
                // Process the command
                process_cmd_local(cmd_line, radio_0);
                // Clear
                cmd_line[0] = 0;
                cmd_line_len = 0;
            }
            // Convenience support for backspace
            else if (c == 8) {
                if (cmd_line_len > 0) {
                    cmd_line[--cmd_line_len] = 0;
                    if (local_echo)
                        printf("%c %c", 8, 8);
                }
            } 
            // All other input added to buffer
            else {
                // Echo
                if (local_echo)
                    printf("%c", c);
                // Accumulate
                cmd_line[cmd_line_len++] = (char)c;
                cmd_line[cmd_line_len] = 0;
            }
            // Look for overflow case
            if (cmd_line_len == 256) {
                printf("error\n");
                cmd_line_len = 0;
            }
        }
    }
}
