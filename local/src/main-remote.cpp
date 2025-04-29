#include <cstring>

#include "kc1fsz-tools/Log.h"
#include "kc1fsz-tools/Common.h"
#include "kc1fsz-tools/rp2040/PicoClock.h"
#include "kc1fsz-tools/rp2040/PicoPollTimer.h"
#include "kc1fsz-tools/rp2040/SX1276Driver.h"

#include "main-remote.h"

using namespace kc1fsz;

static const unsigned int workareaSize = 4096;
static uint8_t workarea[workareaSize];

void flash(const uint8_t* data, uint32_t flash_offset, uint32_t flash_size) {  
}

void process_cmd_remote(const uint8_t* msg, unsigned int msg_len, Log& log, SX1276Driver& radio) {

    if (msg_len >= 4) {

        // Little endian!
        uint16_t cmd = msg[0] | (msg[1] << 8);
        uint16_t seq = msg[2] | (msg[3] << 8);

        // Init
        if (cmd == 1) {
            uint8_t resp[5];
            resp[0] = 1;
            resp[1] = 0;
            resp[2] = msg[2];
            resp[3] = msg[3];
            resp[4] = 0;
            radio.send(resp, 5);
            return;
        }

        // Reset
        else if (cmd == 2) {
            uint8_t resp[5];
            resp[0] = 2;
            resp[1] = 0;
            resp[2] = msg[2];
            resp[3] = msg[3];
            resp[4] = 0;
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

            log.info("Workarea write seq %d, off %d, sz %d", (int)seq, (int)offset, (int)size);

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

            log.info("Flash seq %d, off %d, sz %d", (int)seq, (int)offset, (int)size);

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

            // The actual copy
            flash(workarea, offset, size);

            // Send back a response
            uint8_t resp[5];
            resp[0] = 4;
            resp[1] = 0;
            resp[2] = msg[2];
            resp[3] = msg[3];
            resp[4] = 0;
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
