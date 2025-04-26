#ifndef _main_remote_h
#define _main_remote_h

#include <cstdint>

namespace kc1fsz {
class SX1276Driver;
class Log;
}

void process_cmd_remote(const uint8_t* msg, unsigned int msg_len, kc1fsz::Log& log, kc1fsz::SX1276Driver& radio);

#endif
