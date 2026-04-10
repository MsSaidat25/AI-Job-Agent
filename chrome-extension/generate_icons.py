"""Generate PNG icon files for the Chrome extension."""
import struct
import zlib


def create_png(size, bg_color=(34, 34, 34), accent=(242, 204, 13)):
    """Create a briefcase icon PNG at the given size."""
    width = height = size
    pixels = []
    for y in range(height):
        row = []
        for x in range(width):
            nx = x / width
            ny = y / height
            r, g, b, a = bg_color[0], bg_color[1], bg_color[2], 255

            body_left, body_right = 0.15, 0.85
            body_top, body_bottom = 0.35, 0.80
            handle_left, handle_right = 0.35, 0.65
            handle_top, handle_bottom = 0.15, 0.40
            handle_inner_left, handle_inner_right = 0.42, 0.58
            handle_inner_top, handle_inner_bottom = 0.22, 0.35
            clasp_left, clasp_right = 0.42, 0.58
            clasp_top, clasp_bottom = 0.50, 0.62

            if body_left <= nx <= body_right and body_top <= ny <= body_bottom:
                r, g, b = accent
            if handle_left <= nx <= handle_right and handle_top <= ny <= handle_bottom:
                r, g, b = accent
            if (
                handle_inner_left <= nx <= handle_inner_right
                and handle_inner_top <= ny <= handle_inner_bottom
            ):
                r, g, b = bg_color
            if clasp_left <= nx <= clasp_right and clasp_top <= ny <= clasp_bottom:
                r, g, b = (
                    int(accent[0] * 0.7),
                    int(accent[1] * 0.7),
                    int(accent[2] * 0.7),
                )

            cx, cy = width / 2, height / 2
            dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            radius = width * 0.48
            if dist > radius:
                a = 0

            row.append((r, g, b, a))
        pixels.append(row)

    def chunk(chunk_type, data):
        c = chunk_type + data
        crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + c + crc

    header = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    raw_data = b""
    for row in pixels:
        raw_data += b"\x00"
        for r2, g2, b2, a2 in row:
            raw_data += struct.pack("BBBB", r2, g2, b2, a2)
    compressed = zlib.compress(raw_data, 9)
    return header + chunk(b"IHDR", ihdr) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")


if __name__ == "__main__":
    for size in [16, 48, 128]:
        data = create_png(size)
        with open(f"icons/icon{size}.png", "wb") as f:
            f.write(data)
        print(f"Created icon{size}.png ({len(data)} bytes)")
