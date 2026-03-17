#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <cstdint>
#include <cmath>
#include <cstring>
#include <algorithm>

const int MAX_DEPTH = 64;

struct AIHeader {
    uint32_t version;
    float    worldWidth;
    uint32_t reserved1;
    uint32_t reserved2;
    float    worldHeight;
    float    scale;
};

struct Stats {
    size_t total_nodes = 0;
    size_t leaf_nodes = 0;
    size_t internal_nodes = 0;
    int max_depth = 0;
    size_t max_node_offset = 0;
    size_t errors = 0;
    size_t depth_limit_hits = 0;
    size_t skipped_children = 0;
};

void parse_node(const std::vector<uint8_t>& data,
    uint32_t offset,
    float parent_x,
    float parent_y,
    float parent_z,
    int child_idx,
    int depth,
    std::ostringstream& out,
    Stats& stats)
{
    if (depth > MAX_DEPTH) {
        out << "Error: depth limit exceeded at offset 0x" << std::hex << offset
            << std::dec << " (file size " << data.size() << ")\n";
        ++stats.depth_limit_hits;
        ++stats.errors;
        return;
    }

    if (offset + 12 > data.size()) {
        out << "Error: offset 0x" << std::hex << offset
            << std::dec << " out of bounds (file size " << data.size() << ")\n";
        ++stats.errors;
        return;
    }

    const int32_t* words = reinterpret_cast<const int32_t*>(data.data() + offset);
    int32_t w0 = words[0];
    int32_t w1 = words[1];
    int32_t w2 = words[2];
    int32_t w3 = 0;

    if (w2 != 0) {
        w3 = words[3];
    }

    ++stats.total_nodes;
    stats.max_depth = std::max(stats.max_depth, depth);
    stats.max_node_offset = std::max(stats.max_node_offset, static_cast<size_t>(offset));

    float x, y, z;
    if (depth == 0) {
        x = parent_x;
        y = parent_y;
        z = parent_z;
    }
    else {
        float half = parent_z * 0.5f;
        x = parent_x;
        y = parent_y;
        if (child_idx == 1 || child_idx == 3) y += half;
        if (child_idx == 2 || child_idx == 3) x -= half;
        z = half;
    }

    out << offset << ',' << depth << ',' << child_idx << ','
        << w0 << ',' << w1 << ',' << w2 << ',' << w3 << ','
        << x << ',' << y << ',' << z << ','
        << (w2 == 0 ? "LEAF" : "INTERNAL") << '\n';

    if (w2 == 0) {
        ++stats.leaf_nodes;
        return;
    }

    ++stats.internal_nodes;

    if (w3 == -1) {
        ++stats.skipped_children;
        return;
    }

    uint32_t child0_off = offset + 16;
    parse_node(data, child0_off, x, y, z, 0, depth + 1, out, stats);

    uint32_t p1 = offset + 16 + static_cast<uint32_t>(w3);
    if (p1 + 4 > data.size()) {
        out << "Error: p1 out of bounds at parent offset 0x" << std::hex << offset
            << std::dec << " (file size " << data.size() << ")\n";
        ++stats.errors;
        return;
    }
    int32_t offset2 = *reinterpret_cast<const int32_t*>(data.data() + p1);
    if (offset2 != -1) {
        uint32_t child1_off = p1 + 4;
        parse_node(data, child1_off, x, y, z, 1, depth + 1, out, stats);
    }
    else {
        ++stats.skipped_children;
    }

    if (offset2 != -1) {
        uint32_t p2 = p1 + 4 + static_cast<uint32_t>(offset2);
        if (p2 + 4 > data.size()) {
            out << "Error: p2 out of bounds at parent offset 0x" << std::hex << offset
                << std::dec << " (file size " << data.size() << ")\n";
            ++stats.errors;
            return;
        }
        int32_t offset3 = *reinterpret_cast<const int32_t*>(data.data() + p2);
        if (offset3 != -1) {
            uint32_t child2_off = p2 + 4;
            parse_node(data, child2_off, x, y, z, 2, depth + 1, out, stats);
        }
        else {
            ++stats.skipped_children;
        }

        if (offset3 != -1) {
            uint32_t p3 = p2 + 4 + static_cast<uint32_t>(offset3) + 4;
            uint32_t child3_off = p3;
            parse_node(data, child3_off, x, y, z, 3, depth + 1, out, stats);
        }
        else {
            ++stats.skipped_children;
        }
    }
    else {
        // offset2 == -1, children 2 and 3 already skipped
    }
}

int main(int argc, char* argv[]) {
    if (argc < 3) {
        std::cerr << "Usage: " << argv[0] << " <input.ai> <output.csv>\n";
        return 1;
    }

    std::ifstream file(argv[1], std::ios::binary);
    if (!file) {
        std::cerr << "Cannot open input file\n";
        return 1;
    }
    std::vector<uint8_t> data((std::istreambuf_iterator<char>(file)),
        std::istreambuf_iterator<char>());
    file.close();

    if (data.size() < sizeof(AIHeader)) {
        std::cerr << "File too small to contain a header\n";
        return 1;
    }

    AIHeader header;
    std::memcpy(&header, data.data(), sizeof(header));
    std::cout << "Version: " << header.version << "\n";
    std::cout << "WorldWidth: " << header.worldWidth << "\n";
    std::cout << "WorldHeight: " << header.worldHeight << "\n";
    std::cout << "Scale: " << header.scale << "\n";
    std::cout << "File size: " << data.size() << " bytes\n";

    uint32_t root_offset = 0x18;

    float root_x = header.worldWidth / 2.0f;
    float root_y = header.worldHeight / 2.0f;
    float root_z = std::max(header.worldWidth, header.worldHeight) / 2.0f;

    std::ostringstream out_buffer;
    out_buffer << "offset,depth,child_idx,word0,word1,word2,word3,x,y,z,type\n";

    Stats stats;
    parse_node(data, root_offset, root_x, root_y, root_z, -1, 0, out_buffer, stats);

    size_t last_node_end = stats.max_node_offset + 12;
    if (last_node_end < data.size()) {
        out_buffer << "\n# Warning: parsed data ends at offset " << last_node_end
            << ", but file size is " << data.size()
            << " bytes. " << (data.size() - last_node_end) << " bytes of trailing data may be unused.\n";
    }
    else if (last_node_end > data.size()) {
        out_buffer << "\n# Error: last node extends beyond file end.\n";
    }

    out_buffer << "\n# Summary:\n"
        << "# Total nodes: " << stats.total_nodes << "\n"
        << "# Leaf nodes: " << stats.leaf_nodes << "\n"
        << "# Internal nodes: " << stats.internal_nodes << "\n"
        << "# Maximum depth: " << stats.max_depth << "\n"
        << "# Last node header end offset: " << last_node_end << "\n"
        << "# Depth limit hits: " << stats.depth_limit_hits << "\n"
        << "# Skipped children (due to -1 offsets): " << stats.skipped_children << "\n"
        << "# Errors: " << stats.errors << "\n";

    std::ofstream out(argv[2]);
    if (!out) {
        std::cerr << "Cannot open output file\n";
        return 1;
    }
    out << out_buffer.str();
    out.close();

    std::cout << "\nParsing completed.\n"
        << "Total nodes: " << stats.total_nodes << "\n"
        << "Leaf nodes: " << stats.leaf_nodes << "\n"
        << "Internal nodes: " << stats.internal_nodes << "\n"
        << "Maximum depth: " << stats.max_depth << "\n"
        << "Last node header end offset: " << last_node_end << "\n"
        << "Depth limit hits: " << stats.depth_limit_hits << "\n"
        << "Skipped children: " << stats.skipped_children << "\n"
        << "Errors: " << stats.errors << "\n";
    if (last_node_end < data.size()) {
        std::cout << "Warning: " << (data.size() - last_node_end) << " bytes of trailing data not parsed.\n";
    }
    std::cout << "Output written to " << argv[2] << "\n";

    return stats.errors ? 1 : 0;
}