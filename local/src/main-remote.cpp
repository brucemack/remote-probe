#include <cstring>

#include "kc1fsz-tools/Log.h"
#include "kc1fsz-tools/Common.h"
#include "kc1fsz-tools/rp2040/PicoClock.h"
#include "kc1fsz-tools/rp2040/PicoPollTimer.h"
#include "kc1fsz-tools/rp2040/SX1276Driver.h"

#include "kc1fsz-tools/rp2040/SWDDriver.h"
#include "kc1fsz-tools/SWDUtils.h"

#include "main-remote.h"

using namespace kc1fsz;

static const unsigned int workareaSize = 4096;
static uint8_t workarea[workareaSize];

int do_init(Log& log, SWDDriver& swd) {
    log.info("Init");
    swd.init();
    return swd.connect();
}

int do_reset(Log& log, SWDDriver& swd) {
    log.info("Reset");
    return reset(swd);
}

int do_reset_into_debug(Log& log, SWDDriver& swd) {
    log.info("Reset Into Debug");
    return reset_into_debug(swd);
}

int do_flash(const uint8_t* data, uint32_t flash_offset, uint32_t flash_size, Log& log, SWDDriver& swd) {
    log.info("Flash %08X/%08X", flash_offset, flash_size);
    return flash_and_verify(swd, flash_offset, data, flash_size);
}

void process_cmd_remote(const uint8_t* msg, unsigned int msg_len, Log& log, SX1276Driver& radio, SWDDriver& swd) {

    if (msg_len >= 4) {

        // Little endian!
        uint16_t cmd = msg[0] | (msg[1] << 8);
        uint16_t seq = msg[2] | (msg[3] << 8);

        // Init
        if (cmd == 1) {
            int rc = do_init(log, swd);
            uint8_t resp[5];
            resp[0] = 1;
            resp[1] = 0;
            resp[2] = msg[2];
            resp[3] = msg[3];
            if (rc == 0)
                resp[4] = 0;
            else 
                resp[4] = 1;
            radio.send(resp, 5);
            return;
        }

        // Reset
        else if (cmd == 2) {
            int rc = do_reset(log, swd);
            uint8_t resp[5];
            resp[0] = 2;
            resp[1] = 0;
            resp[2] = msg[2];
            resp[3] = msg[3];
            if (rc == 0)
                resp[4] = 0;
            else
                resp[4] = 1;
            radio.send(resp, 5);
            return;
        }

        // Reset Into Debug
        else if (cmd == 5) {
            int rc = do_reset_into_debug(log, swd);
            uint8_t resp[5];
            resp[0] = 5;
            resp[1] = 0;
            resp[2] = msg[2];
            resp[3] = msg[3];
            if (rc == 0)
                resp[4] = 0;
            else 
                resp[4] = 1;
            radio.send(resp, 5);
            return;
        }

        // Workarea update
        else if (cmd == 3) {

            uint16_t offset = msg[4] | (msg[5] << 8);
            uint16_t size = msg_len - 6;

            // Sanity check
            if ((offset + size) > workareaSize) {
                uint8_t resp[5];
                resp[0] = 3;
                resp[1] = 0;
                resp[2] = msg[2];
                resp[3] = msg[3];
                resp[4] = 1;
                radio.send(resp, 5);
                return;
            }

            //log.info("Workarea write seq %d, off %d, sz %d", (int)seq, (int)offset, (int)size);

            // The actual copy
            memcpy(&(workarea[offset]), msg + 6, size);

            // Send back a response
            uint8_t resp[5];
            resp[0] = 3;
            resp[1] = 0;
            resp[2] = msg[2];
            resp[3] = msg[3];
            resp[4] = 0;
            radio.send(resp, 5);
        } 

        // Flash
        else if (cmd == 4) {

            uint32_t offset = msg[4] | (msg[5] << 8) | (msg[6] << 16) | (msg[7] << 24);
            uint16_t size = msg[8] | (msg[9] << 8);          

            //log.info("Flash seq %d, off %d, sz %d", (int)seq, (int)offset, (int)size);

            // Sanity check
            if (size > workareaSize) {
                uint8_t resp[5];
                resp[0] = 4;
                resp[1] = 0;
                resp[2] = msg[2];
                resp[3] = msg[3];
                resp[4] = 1;
                radio.send(resp, 5);
                return;
            }

            // The actual flash
            int rc = do_flash(workarea, offset, size, log, swd);

            // Send back a response
            uint8_t resp[5];
            resp[0] = 4;
            resp[1] = 0;
            resp[2] = msg[2];
            resp[3] = msg[3];
            if (rc == 0)
                resp[4] = 0;
            else 
                resp[4] = 1;
            radio.send(resp, 5);
        } 
        else {
            log.error("Unknown");
            prettyHexDump(msg, msg_len, std::cout);
        }
    }
    else {
        log.error("Unknown");
        prettyHexDump(msg, msg_len, std::cout);
    }
}
