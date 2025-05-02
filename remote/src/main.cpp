/**
 * Copyright (C) Bruce MacKinnon, 2025
 */
#include <stdio.h>
#include <stdlib.h>

#include "pico/stdlib.h"

#include "hardware/gpio.h"
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

static int int_pin_1 = 0;
static volatile bool int_flag_1 = false;

static void gpio_callback(uint gpio, uint32_t events) {
    if (gpio == int_pin_1)
        int_flag_1 = true;
}

int main(int, const char**) {

    //stdio_init_all();
    stdio_uart_init_full(uart0, 115200, 0, 1);

    gpio_init(LED_PIN);
    gpio_set_dir(LED_PIN, GPIO_OUT);
    // Startup diagnostic flash      
    gpio_put(LED_PIN, 1);
    sleep_ms(500);
    gpio_put(LED_PIN, 0);
    sleep_ms(500);

    PicoClock clock;
    PicoPollTimer radio_poll;
    // Fast poll every 1ms
    radio_poll.setIntervalUs(1000);
    Log log;

    log.info("Remote Probe (Remote Node)");

    // ----- Radio 1 Hookup -----

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
    gpio_set_irq_enabled_with_callback(int_pin_1, GPIO_IRQ_EDGE_RISE, true, &gpio_callback);

    // The CS pin is not behaving the way we want, so drive manually
    gpio_init(spi_cs_pin_1);
    gpio_set_dir(spi_cs_pin_1, GPIO_OUT);
    gpio_put(spi_cs_pin_1, 1);

    gpio_set_function(spi_sck_pin_1, GPIO_FUNC_SPI);
    gpio_set_function(spi_mosi_pin_1, GPIO_FUNC_SPI);
    gpio_set_function(spi_miso_pin_1, GPIO_FUNC_SPI);
    spi_init(spi1, 500000);

    SX1276Driver radio_1(log, clock, reset_pin_1, spi_cs_pin_1, spi1);

    // ----- SWD Hookup -----

    gpio_init(CLK_PIN);
    gpio_set_dir(CLK_PIN, GPIO_OUT);        
    gpio_put(CLK_PIN, 0);
    gpio_init(DIO_PIN);
    gpio_set_dir(DIO_PIN, GPIO_OUT);        
    gpio_put(DIO_PIN, 0);
    
    SWDDriver swd(CLK_PIN, DIO_PIN);

    // Force a few poll cycles to get the radio through initialization
    radio_1.event_poll();
    radio_1.event_tick();

    if (radio_1.isRadioInitGood())
        log.info("Radio initialized");
    else
        log.error("Radio failed to initialize");

    while (true) {        

        // Look for interrupt activity and notify the radios
        uint32_t int_state = save_and_disable_interrupts();
        if (int_flag_1) {
            radio_1.event_int();
            int_flag_1 = false;
        }        
        restore_interrupts(int_state);

        // Fast poll
        radio_1.event_poll();

        // Slow poll
        if (radio_poll.poll()) {
            radio_1.event_tick();
        }

        // ----- Handle radio receive activity -----

        uint8_t buf[LARGEST_PAYLOAD];
        unsigned int buf_len = LARGEST_PAYLOAD;
        short rssi;
        
        if (radio_1.popReceiveIfNotEmpty(&rssi, buf, &buf_len))
            process_cmd_remote(rssi, buf, buf_len, log, radio_1, swd);
    }
}
