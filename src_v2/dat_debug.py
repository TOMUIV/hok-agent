import struct, json

with open('/hok_env/hok/hok1v1/config.dat', 'rb') as f:
    data = f.read()

print(f'Total: {len(data)} bytes')

pos = 0
entry_count = 0
while pos < len(data) - 8:
    total_size = struct.unpack('<I', data[pos:pos+4])[0]
    name_len = struct.unpack('<I', data[pos+4:pos+8])[0]
    if pos + total_size > len(data):
        break
    name = data[pos+8:pos+8+name_len].decode('utf-8', errors='replace')
    content = data[pos+8+name_len:pos+total_size]
    entry_count += 1
    try:
        val_obj = json.loads(content.decode('utf-8'))
        val_type = type(val_obj).__name__
        content_preview = json.dumps(val_obj, ensure_ascii=False)[:60]
    except:
        val_type = 'not_json'
        try:
            content_preview = content.decode('utf-8', errors='replace')[:60]
        except:
            content_preview = repr(content[:30])
    print(f'[{entry_count:3d}] {name:60s} size={total_size:6d} type={val_type:10s} val={content_preview}')
    if entry_count >= 55:
        break
    pos += total_size

print(f'\nParsed {entry_count} entries, consumed {pos} bytes of {len(data)}')
