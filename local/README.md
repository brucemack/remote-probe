Project Setup
=============

        git submodule update --init --recursive
        mkdir build
        cd build
        cmake -DPICO_BOARD=pico ..

Build/Run
=========

        make main
        ~/git/openocd/src/openocd -s ~/git/openocd/tcl -f interface/cmsis-dap.cfg -f target/rp2040.cfg -c "adapter speed 500" -c "program main.elf verify reset exit"

Hardware Setup
==============

Radio 0 Hookup

* spi_sck_pin_0 = GP2
* spi_mosi_pin_0 = GP3
* spi_miso_pin_0 = GP4
* spi_cs_pin_0 = GP5
* (GND)
* reset_pin_0 = GP6
* int_pin_0 = GP7

Radio 1 Hookup

* spi_sck_pin_1 = GP10
* spi_mosi_pin_1 = GP11
* spi_miso_pin_1 = GP12
* spi_cs_pin_1 = GP13
* (GND)
* reset_pin_1 = GP14
* int_pin_1 = GP15

WARS Radio Board 2022-04 Hookup (J1)

* 1: 3.3V out
* 3: 
* 5: 
* 7: 5V in 
* 9: 
* 11: 
* 13: GND
* 15: GND

* 2: Radio interrupt out
* 4: Radio reset in
* 6: Radio SPI CS in
* 8: Radio SPI SCK in 
* 10: Radio SPI MOSI in
* 12: Radio SPI MISO out 
* 14: GND
* 16: GND

Notes
=====

* Read lines from STDIN
        - Parse command, build packet for LoRa
* Listen for inbound LoRa messages
        - Convert to text and show on STDOUT

Commands (all \n terminated)

* @configure - For configuring radio
* @status - For getting status 
* @send xxxxx (data in base-64 format)
* @ping 

Statuses (all \n terminated)

* $status l ccc mmmm (link status, send capacity, message)
* $receive ssss rrrr xxxxx (ssss=snr, rrrr=rssi, xxxx data in base-64 format)
* $send-clear When send buffer transitions to zero.
* $pong