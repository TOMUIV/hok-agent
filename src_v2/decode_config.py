import struct
with open('/hok_env/hok/hok1v1/config.dat', 'rb') as f:
    data = f.read()
print(f'Total length: {len(data)}')
pos = 0
while pos < len(data) - 8:
    total_len = struct.unpack('<I', data[pos:pos+4])[0]
    name_len = struct.unpack('<I', data[pos+4:pos+8])[0]
    if pos + 8 + name_len > len(data):
        break
    name = data[pos+8:pos+8+name_len].decode('utf-8', errors='replace')
    print(f'  {name:60s} total={total_len} name_len={name_len}')
    pos += 8 + name_len + (total_len - name_len)
