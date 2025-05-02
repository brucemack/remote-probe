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

Radio 1 Hookup

* spi_sck_pin_1 = GP10
* spi_mosi_pin_1 = GP11
* spi_miso_pin_1 = GP12
* spi_cs_pin_1 = GP13
* (GND)
* reset_pin_1 = GP14
* int_pin_1

SWD Hookup

* CLK_PIN = GP16
* DIO_PIN = GP17

WARS Radio Board 2022-04 Hookup (J1)
====================================

Right Column

* 1: 3.3V out, used for onboard SX1276 module, but could also be used to power MCU.
* 3: Raw panel input, not used for anything on board except panel sense.
* 5: Raw panel input, could be used for charge controller IN+.
* 7: 4-6V supply in, could be taken from charge controller OUT+.
* 9: Panel sense out, could be sent to ADC for monitoring.
* 11: 4-6V supply sense out, could bne sent to ADC for monitoring.
* 13: GND (i.e. panel ground)
* 15: GND (i.e. charge controller OUT-)

Left Column

* 2: Radio interrupt out
* 4: Radio reset in
* 6: Radio SPI CS in
* 8: Radio SPI SCK in
* 10: Radio SPI MOSI in
* 12: Radio SPI MISO out
* 14: GND
* 16: GND
