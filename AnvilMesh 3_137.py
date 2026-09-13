# ==========================================
# AC Odyssey MESH IMPORTER - VERSION 3.137
# ==========================================

bl_info = {
    "name": "AnvilSoft Mesh Step Importer",
    "author": "AI Assistant",
    "version": (3, 137),
    "blender": (5, 2, 0),
    "location": "View3D > Sidebar > AnvilSoft Mesh",
    "description": "Interactive binary importer.",
    "category": "Import-Export",
}
#v3.127 is the fully finished Importer
#Corrected UV scaling to -1 to 1.0
# Added Section 53 BlendShape Catalog decode

import bpy
import os
import struct
import mathutils

FMT_UINT16 = chr(60) + chr(72)
FMT_UINT32 = chr(60) + chr(73)
FMT_UINT64 = chr(60) + chr(81)
FMT_UINT8  = chr(60) + chr(66)
FMT_MATRIX = "<16f" 
MODE_RB    = chr(114) + chr(98)

MARKERS = {
    0x9EF0E7A1: "DEFORM_BONE_MARKER",
    0x3FD52D67: "HELPER_BONE_MARKER",
    0xC5B003DC: "MORPH_TARGET_MARKER",
    0xC2023DA2: "CLOTH_PHYSICS_MARKER",
    0x92E29AB6: "VERTEX_COLOR_MARKER",
    0x891A367C: "MESH_REGISTRY_MARKER",
    0xFD4C3871: "TEXTURE_MAP_MARKER",
    0xFC9E1595: "TANGENT_SPACE_MARKER",
    0xC351EE43: "TOPOLOGY_MAP_MARKER",
    0x07B19A87: "MESH_CONTAINER_MARKER",
    0x0645ABB5: "SHADER_OVERRIDE_MARKER",
    0xA57387EF: "MESH_PRIMITIVE_MARKER",
    0x415D9568: "GLOBAL_BOUNDING_MARKER",
    0x0B1D34C1: "MATERIAL_SECTION_MARKER"
}

class AnvilState:
    #Change this to your default direcory if required
    file_path = "C:/Users/Documents/BlksmthTemp/Sample LOD0.Mesh"
    sections_map = [] 
    current_index = -1
    deform_bones_data = []
    active_proxy_obj = None
    
    total_vertices = 0
    total_faces = 0
    extracted_vertices = []
    extracted_faces = []

def clear_scene_tree():
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for block in [bpy.data.meshes, bpy.data.armatures]:
        for item in block:
            block.remove(item)
    print("Blender scene tree cleared.")

def parse_deform_bone_payload(f, payload_size):
    raw_name_tuple = struct.unpack(FMT_UINT32, f.read(4))
    bone_name_int = raw_name_tuple[0]
    bone_name_str = str(bone_name_int)
    matrix_floats = struct.unpack(FMT_MATRIX, f.read(64))
    #print(f"matrix_floats = {matrix_floats} \n")
    remaining_bytes = payload_size - 68
    if remaining_bytes > 0:
        f.read(remaining_bytes)
    AnvilState.deform_bones_data.append({
        'name': bone_name_str,
        'matrix': matrix_floats
    })
    return "Parsed Deform Bone: " + bone_name_str

def parse_primitive_payload(f):
    f.read(8)
    v_tup = struct.unpack(FMT_UINT32, f.read(4))
    AnvilState.total_vertices = v_tup[0]
    f.read(4)
    f_tup = struct.unpack(FMT_UINT32, f.read(4))
    AnvilState.total_faces = f_tup[0]
    f.read(28)
    return "TotalVertices: " + str(AnvilState.total_vertices) + " | TotalFaces: " + str(AnvilState.total_faces)

def parse_material_payload(f):
    flag = struct.unpack(FMT_UINT8, f.read(1))[0]
    subtype = struct.unpack(FMT_UINT32, f.read(4))[0]
    rep_v = struct.unpack(FMT_UINT16, f.read(2))[0]
    f.read(3)
    mat_id = struct.unpack(FMT_UINT64, f.read(8))[0]
    return "Subtype: " + str(subtype) + " | MatID: " + str(mat_id)

def build_blender_mesh_object():
    if not AnvilState.extracted_vertices or not AnvilState.extracted_faces:
        return "Geometry data incomplete. Cannot build mesh."
        
    mesh_data = bpy.data.meshes.new("Cloth_Mesh_Data")
    mesh_obj = bpy.data.objects.new("Cloth_Mesh", mesh_data)
    bpy.context.scene.collection.objects.link(mesh_obj)
    
    mesh_data.from_pydata(AnvilState.extracted_vertices, [], AnvilState.extracted_faces)
    mesh_data.update()
    return "Generated 'Cloth_Mesh' asset in viewport successfully!"

import struct
import mathutils
import bpy

import struct
import mathutils

import struct
import mathutils
import bpy

def parse_section_53_blendshape_list(f, block_size):
    """
    Parses Section 53 (0x92E29AB6) to extract the structural catalog IDs 
    for the embedded mesh BlendShapes / Shape Keys.
    """
    print(f"\n[DEBUG SECTION 53] Parsing BlendShape Catalog Header | Size: {block_size} bytes")
    
    # Verify the incoming block matches our exact 25-byte structure
    if block_size < 5:
        print(f"  [ERROR] Section 53 payload size is smaller than minimum 5 bytes.")
        return []
        
    try:
        # Read the core metadata tracking headers (already matched by master index loop)
        #sec_num = struct.unpack("<I", f.read(4))[0]
        #padding = struct.unpack("<I", f.read(4))[0]
        #sec_type = struct.unpack("<I", f.read(4))[0]
        
        # Read the total count of registered shapes (Byte 12-15)
        num_blendshapes = struct.unpack("<I", f.read(4))[0]
        print(f"  -> Total Declared BlendShapes: {num_blendshapes}")
        
        blendshape_ids = []
        for i in range(num_blendshapes):
            # Unpack the unique 4-byte engine identifier hash for each shape key
            shape_id = struct.unpack("<I", f.read(4))[0]
            blendshape_ids.append(shape_id)
            print(f"     * BlendShape [{i}] ID: 0x{shape_id:08X}")
        print(f"blendshapes: {num_blendshapes}")
        # Consume the trailing 1-byte null termination flag to maintain structural parity
        termination_byte = f.read(1)
        
        return blendshape_ids
        
    except Exception as e:
        print(f"  [ERROR] Failed to parse Section 53: {e}")
        return []


def parse_section_891A367C(f, size):
    """
    Parses Section 55: SkinWrapProxyMesh (0x891A367C)
    Extracts explicit proxy deformation points and subsequent sub-target counts.
    """
    import struct
    
    extracted_data = {
        'vertices': [],
        'target_count': 0,
        'status': 'Success'
    }
    
    # 1. Read Element Count
    num_elements_raw = f.read(4)
    if not num_elements_raw or len(num_elements_raw) < 4:
        extracted_data['status'] = 'Failed to read element count'
        return extracted_data
        
    num_elements = struct.unpack("<I", num_elements_raw)[0]
    
    # 2. Extract X, Y, Z Floating-point coordinates
    for _ in range(num_elements):
        coord_bytes = f.read(12)  # 3 floats * 4 bytes
        if len(coord_bytes) == 12:
            x, y, z = struct.unpack("<fff", coord_bytes)
            # Match whatever spatial/axis transformation you used for 0x07B19A87
            mody = -z
            modz = y
            extracted_data['vertices'].append((x, mody, modz))
            
    # 3. Read the 20-byte footer alignment trailing block
    footer_bytes = f.read(20)
    if len(footer_bytes) == 20:
        extracted_data['target_count'] = struct.unpack("<I", footer_bytes[16:20])[0]
    else:
        extracted_data['status'] = 'Truncated or missing footer alignment'
    
    return extracted_data

def build_proxy_point_cloud(coords, name="Proxy_Point_Cloud"):
    """
    Generates a vertex-only point-cloud container object in Blender 
    for visual correlation checks against your main skin.
    """
    mesh = bpy.data.meshes.new(name=name)
    obj = bpy.data.objects.new(name, mesh)
    
    # Link object to the active layer collection
    bpy.context.collection.objects.link(obj)
    
    # Generate vertices without linking edges or faces
    mesh.from_pydata(coords, [], [])
    mesh.update()
    
    return obj

def parse_section_C2023DA2(f, size):
    """
    Parses Section 56-59: SkinWrapProxyMeshTarget (0xC2023DA2)
    Extracts subset tracking IDs and transforms 16-bit half-precision float blocks
    into 3D vector offset coordinates matching the 842 proxy vertices.
    """
    import struct
    
    extracted_data = {
        'target_id': 0,
        'vectors': [],
        'status': 'Success'
    }
    
    # 1. Read the explicit Target ID
    target_id_raw = f.read(4)
    if not target_id_raw or len(target_id_raw) < 4:
        extracted_data['status'] = 'Failed to read Target ID'
        return extracted_data
    extracted_data['target_id'] = struct.unpack("<I", target_id_raw)[0]
    
    # 2. Read Element Count (Total number of half-floats, e.g., 2526)
    num_elements_raw = f.read(4)
    if not num_elements_raw or len(num_elements_raw) < 4:
        extracted_data['status'] = 'Failed to read element count'
        return extracted_data
    num_elements = struct.unpack("<I", num_elements_raw)[0]
    
    # 3. Read the half-precision floats as 3D (X, Y, Z) vectors
    # 2,526 elements / 3 components = 842 vectors
    num_vectors = num_elements // 3
    
    for _ in range(num_vectors):
        # 3 components * 2 bytes each = 6 bytes total per vector
        coord_bytes = f.read(6)
        if len(coord_bytes) == 6:
            # "e" represents a 16-bit half-precision float in struct
            vx, vy, vz = struct.unpack("<eee", coord_bytes)
            
            # Apply the exact same orientation modifications you used for Section 55
            mody = -vz
            modz = vy
            extracted_data['vectors'].append((vx, mody, modz))
            
    # 4. Consume any remaining padding/termination bytes (like the 0x00 in Sec 59)
    bytes_read = 8 + (num_elements * 2)
    if bytes_read < size:
        extra_bytes = size - bytes_read
        f.read(extra_bytes) # Safely flushes trailing bytes out of the stream
        
    return extracted_data
    
def parse_section_3FD52D67(f, size):
    """
    Parses Section 61-68: SWLMPWIndices (0x3FD52D67)
    Extracts bitmask tables and variable-width skin wrap index blocks.
    """
    import struct
    
    extracted_data = {
        'sub_block_1_size': 0,
        'sub_block_2_size': 0,
        'raw_indices_count': 0,
        'status': 'Success'
    }
    
    try:
        start_pos = f.tell()
        
        # --- PROCESS SUB-BLOCK 1 ---
        sb1_size_raw = f.read(4)
        if not sb1_size_raw or len(sb1_size_raw) < 4:
            extracted_data['status'] = 'Truncated Sub-Block 1 Size'
            return extracted_data
            
        sb1_size = struct.unpack("<I", sb1_size_raw)[0]
        extracted_data['sub_block_1_size'] = sb1_size
        
        # Read the raw bitmask data channel
        sb1_data = f.read(sb1_size)
        
        # --- PROCESS SUB-BLOCK 2 ---
        sb2_size_raw = f.read(4)
        if not sb2_size_raw or len(sb2_size_raw) < 4:
            extracted_data['status'] = 'Truncated Sub-Block 2 Size'
            return extracted_data
            
        sb2_size = struct.unpack("<I", sb2_size_raw)[0]
        extracted_data['sub_block_2_size'] = sb2_size
        
        # Read the indices array payload safely
        sb2_data = f.read(sb2_size)
        
        # Let's count how many 16-bit indices can be speculatively read 
        # from the end portion of the block sample
        # We store the total payload size for mapping tracking
        extracted_data['raw_indices_count'] = sb2_size // 2
        
        # --- STREAM SAFE ALIGNMENT CLEARANCE ---
        bytes_read = f.tell() - start_pos
        if bytes_read < size:
            f.read(size - bytes_read) # Completely flushes any remaining trailing bytes
            
    except Exception as e:
        extracted_data['status'] = f"Parsing Error: {str(e)}"
        
    return extracted_data


def apply_swpm_shape_key(target_obj, vectors, key_name):
    """
    Applies extracted half-float displacement vectors as an absolute 
    or relative Shape Key layer on the designated target proxy object.
    """
    import bpy
    
    if not target_obj or target_obj.type != 'MESH':
        return False
        
    # Initialize the Basis key if it doesn't exist yet
    if not target_obj.data.shape_keys:
        basis = target_obj.shape_key_add(name="Basis")
        # REMOVED: basis.user = True (This was causing the crash)
        
    # Add a new named deformation layer
    shape_key = target_obj.shape_key_add(name=key_name)
    # REMOVED: shape_key.user = True (Also read-only)
    
    # Apply the vector offsets to each vertex coordinate
    mesh_verts = target_obj.data.vertices
    for idx, vec in enumerate(vectors):
        if idx < len(mesh_verts):
            base_pos = mesh_verts[idx].co
            # Unpack the unique X, Y, Z tuple parts of the delta vector
            shape_key.data[idx].co = (
                base_pos[0] + vec[0], 
                base_pos[1] + vec[1], 
                base_pos[2] + vec[2]
            )
    return True

def parse_section_FD4C3871(f, size):
    """
    Parses Section 60: SkinWrapLayerMesh (0xFD4C3871)
    Extracts complete 8-Sub-Block structure: 
    Blocks 1-3: Planar Positions, Blocks 4-6: Planar Normals, 
    Block 7: Panel Metrics, Block 8: Panel Ranges.
    """
    import struct
    
    extracted_data = {
        'vertices': [],
        'normals': [],
        'panels': [],
        'status': 'Success'
    }
    
    try:
        start_pos = f.tell()
        
        # === BLOCKS 1-3: PLANAR POSITIONS ===
        num_verts = struct.unpack("<I", f.read(4))[0]
        x_coords = [struct.unpack("<f", f.read(4))[0] for _ in range(num_verts)]
        
        f.read(4) # Skip Y count
        y_coords = [struct.unpack("<f", f.read(4))[0] for _ in range(num_verts)]
        
        f.read(4) # Skip Z count
        z_coords = [struct.unpack("<f", f.read(4))[0] for _ in range(num_verts)]
        
        for i in range(num_verts):
            mody = -z_coords[i]
            modz = y_coords[i]
            extracted_data['vertices'].append((x_coords[i], mody, modz))
            
        # === BLOCKS 4-6: PLANAR NORMALS ===
        f.read(4) # Total group size token
        block_byte_size = struct.unpack("<I", f.read(4))[0]
        num_norm_elements = block_byte_size // 4
        
        nx_coords = [struct.unpack("<f", f.read(4))[0] for _ in range(num_norm_elements)]
        ny_coords = [struct.unpack("<f", f.read(4))[0] for _ in range(num_norm_elements)]
        nz_coords = [struct.unpack("<f", f.read(4))[0] for _ in range(num_norm_elements)]
        
        for i in range(num_norm_elements):
            mod_ny = -nz_coords[i]
            mod_nz = ny_coords[i]
            extracted_data['normals'].append((nx_coords[i], mod_ny, mod_nz))
            
        # === SUB-BLOCK 7: PANEL PARAMETERS (96 BYTES PER ELEMENT) ===
        num_panels = struct.unpack("<I", f.read(4))[0]
        panel_floats_matrix = []
        for _ in range(num_panels):
            # Read 24 floats for this panel zone
            panel_data = struct.unpack(f"<{24}f", f.read(96))
            panel_floats_matrix.append(panel_data)
            
        # === SUB-BLOCK 8: PANEL RUNTIME RANGES (12 BYTES PER ELEMENT) ===
        num_panels_check = struct.unpack("<I", f.read(4))[0]
        for p_idx in range(num_panels_check):
            p_flag, p_count, p_start = struct.unpack("<III", f.read(12))
            extracted_data['panels'].append({
                'panel_index': p_idx,
                'flag': p_flag,
                'vertex_count': p_count,
                'vertex_start': p_start,
                'raw_metrics': panel_floats_matrix[p_idx] if p_idx < len(panel_floats_matrix) else []
            })
            
        # === COORD-ALIGN FOOTER CLEARANCE ===
        bytes_read = f.tell() - start_pos
        if bytes_read < size:
            f.read(size - bytes_read) # Clear out the final 8-byte trailer cleanly
            
    except Exception as e:
        extracted_data['status'] = f"Parsing Error: {str(e)}"
        
    return extracted_data
    
def parse_section_C5B003DC(f, size):
    """
    Parses Sections 69-76: SkinWrapLayerMeshWeights (0xC5B003DC)
    Extracts highly compressed 1-byte (uint8) quantized vertex weights.
    De-quantizes them back to 0.0 - 1.0 floating point scales.
    """
    import struct
    
    extracted_data = {
        'weights': [],
        'status': 'Success'
    }
    
    try:
        # 1. Read Element Count Header (4 Bytes)
        num_elements_raw = f.read(4)
        if not num_elements_raw or len(num_elements_raw) < 4:
            extracted_data['status'] = 'Failed to read weight count header'
            return extracted_data
            
        num_elements = struct.unpack("<I", num_elements_raw)[0]
        
        # 2. Extract sequential 1-byte elements
        # Read the entire array buffer at once for performance
        byte_payload = f.read(num_elements)
        
        if len(byte_payload) == num_elements:
            for b_val in byte_payload:
                # De-quantize: convert integer 0-255 into float 0.0-1.0
                float_weight = b_val / 255.0
                extracted_data['weights'].append(float_weight)
        else:
            extracted_data['status'] = 'Truncated payload array size'
            
        # 3. Clean up any remaining trailing padding bytes up to size boundary
        bytes_processed = 4 + len(byte_payload)
        if bytes_processed < size:
            f.read(size - bytes_processed)
            
    except Exception as e:
        extracted_data['status'] = f"Weights Parsing Error: {str(e)}"
        
    return extracted_data

def parse_section_C351EE43(f, size):
    """
    Parses Section 78: Geometry Layout & Bounding Box Descriptor (0xC351EE43)
    Extracts structural vertex layouts and axis dimensions for upcoming sub-meshes.
    """
    import struct
    
    extracted_data = {
        'version': 0,
        'format': 0,
        'stride_static': 0,
        'stride_dynamic': 0,
        'stride_weights': 0,
        'stride_precompute': 0,
        'center': (0.0, 0.0, 0.0),
        'half_extend': (0.0, 0.0, 0.0),
        'status': 'Success'
    }
    
    try:
        # 1. Layout Properties
        extracted_data['version'] = struct.unpack("<I", f.read(4))[0]
        extracted_data['format'] = struct.unpack("<B", f.read(1))[0]
        extracted_data['stride_static'] = struct.unpack("<I", f.read(4))[0]
        extracted_data['stride_dynamic'] = struct.unpack("<I", f.read(4))[0]
        extracted_data['stride_weights'] = struct.unpack("<I", f.read(4))[0]
        extracted_data['stride_precompute'] = struct.unpack("<I", f.read(4))[0]
        
        # 2. Skip cluster metric count (always 1 in standard envelopes)
        f.read(4) 
        
        # 3. Read Spatially Flip-Transformed Bounding Coordinates
        cx, cy, cz = struct.unpack("<fff", f.read(12))
        hx, hy, hz = struct.unpack("<fff", f.read(12))
        
        # Mirror your standard cloth mesh transformation configuration matrix adjustments
        mody_c, modz_c = -cz, cy
        mody_h, modz_h = -hz, hy
        
        extracted_data['center'] = (cx, mody_c, modz_c)
        extracted_data['half_extend'] = (hx, mody_h, modz_h)
        
        # 4. Flush remaining trailer components up to designated sector length bounds
        bytes_processed = 41 # (4+1+4+4+4+4 + 4 + 12 + 12)
        if bytes_processed < size:
            f.read(size - bytes_processed)
            
    except Exception as e:
        extracted_data['status'] = f"Descriptor Parsing Error: {str(e)}"
        
    return extracted_data

def parse_section_0645ABB5(f, size):
    """
    Parses Section 80: Vertex Stream Layout Blueprint Descriptor (0x0645ABB5)
    Extracts explicit data strides and pipeline allocation tracking quantities.
    """
    import struct
    
    extracted_data = {
        'unk_flag_1': 0,
        'vertex_format': 0,
        'stride_static': 0,
        'stride_dynamic': 0,
        'stride_weights': 0,
        'stride_precompute': 0,
        'bones_per_vertex': 0,
        'blendshapes_qty': 0,
        'skinwrap_weight_qty': 0,
        'layout_offset': 0,
        'stride_precompute_check': 0,
        'termination': 0,
        'status': 'Success'
    }
    
    try:
        # 1. Base Properties (Unpack individual byte configurations)
        extracted_data['unk_flag_1'] = struct.unpack("<B", f.read(1))[0]
        extracted_data['vertex_format'] = struct.unpack("<B", f.read(1))[0]
        
        # 2. Extract explicit memory strides
        extracted_data['stride_static'] = struct.unpack("<I", f.read(4))[0]
        extracted_data['stride_dynamic'] = struct.unpack("<I", f.read(4))[0]
        extracted_data['stride_weights'] = struct.unpack("<I", f.read(4))[0]
        extracted_data['stride_precompute'] = struct.unpack("<I", f.read(4))[0]
        
        # 3. Extract quantity allocations
        extracted_data['bones_per_vertex'] = struct.unpack("<B", f.read(1))[0]
        extracted_data['blendshapes_qty'] = struct.unpack("<B", f.read(1))[0]
        extracted_data['skinwrap_weight_qty'] = struct.unpack("<B", f.read(1))[0]
        extracted_data['layout_offset'] = struct.unpack("<B", f.read(1))[0]
        
        # 4. Extract runtime stride validation token and terminator
        extracted_data['stride_precompute_check'] = struct.unpack("<B", f.read(1))[0]
        extracted_data['termination'] = struct.unpack("<I", f.read(4))[0]
        
        # 5. Safe boundary protection to clear trailing filler bytes
        bytes_processed = 27 # (1+1+4+4+4+4+1+1+1+1+1+4)
        if bytes_processed < size:
            f.read(size - bytes_processed)
            
    except Exception as e:
        extracted_data['status'] = f"Blueprint Parsing Error: {str(e)}"
        
    return extracted_data

def parse_section_A57387EF(f, size):
    """
    Parses Section 81: Geometry Allocation & Inventory Panel (0xA57387EF)
    Extracts global vertex counts, face allocations, and cluster partitions.
    """
    import struct
    
    extracted_data = {
        'total_vertices': 0,
        'total_faces': 0,
        'cluster_count': 0,
        'status': 'Success'
    }
    
    try:
        # 1. Skip initial tracking spacers (2x UInt32)
        f.read(8)
        
        # 2. Extract primary geometry targets
        extracted_data['total_vertices'] = struct.unpack("<I", f.read(4))[0]
        
        # Skip trailing vertex attribute divider spacer
        f.read(4)
        
        extracted_data['total_faces'] = struct.unpack("<I", f.read(4))[0]
        extracted_data['cluster_count'] = struct.unpack("<I", f.read(4))[0]
        
        # 3. Clean up the remaining structural spacer footprint trailing bytes up to size boundary
        bytes_processed = 28 # (8 + 4 + 4 + 4 + 4)
        if bytes_processed < size:
            f.read(size - bytes_processed)
            
    except Exception as e:
        extracted_data['status'] = f"Allocator Layout Parsing Error: {str(e)}"
        
    return extracted_data

def parse_section_0B1D34C1(f, size):
    """
    Parses Section 82: Serialization Footer & Material Descriptor (0x0B1D34C1)
    Extracts known mesh limits and material IDs while storing unknown byte blocks
    intact for exact mirror re-serialization on export.
    """
    import struct
    
    extracted_data = {
        'total_vertices': 0,
        'material_id_1': 0,
        'platform_version': 0,
        'sdk_version': 0,
        'material_id_2': 0,
        'raw_preserved_block_1': b"",  # Holds all bytes between Material 1 and 2
        'raw_preserved_block_2': b"",  # Holds all trailing alignment metadata bytes
        'status': 'Success'
    }
    
    try:
        # 1. Unpack initial preamble blocks
        f.read(2)  # Unknown U16
        f.read(2)  # Unknown U16
        f.read(1)  # Unknown U8
        
        extracted_data['total_vertices'] = struct.unpack("<H", f.read(2))
        
        f.read(2)  # Unknown U16
        f.read(1)  # Unknown U8
        
        # 2. Extract first engine material pointer key
        extracted_data['material_id_1'] = struct.unpack("<Q", f.read(8))
        
        # 3. Extract version targets
        extracted_data['platform_version'] = struct.unpack("<I", f.read(4))
        extracted_data['sdk_version'] = struct.unpack("<I", f.read(4))
        
        # 4. Extract specific variable sequence up to Material 2
        # Separator block contains 1 byte + 17 bytes = 18 bytes
        extracted_data['raw_preserved_block_1'] = f.read(18)
        
        # 5. Extract second repeating instance of material link key
        extracted_data['material_id_2'] = struct.unpack("<Q", f.read(8))
        
        # 6. Preserved Trailing Matrix (Read everything else remaining up to size boundary)
        bytes_read_so_html = 2 + 2 + 1 + 2 + 2 + 1 + 8 + 4 + 4 + 18 + 8
        if bytes_read_so_html < size:
            remaining_bytes = size - bytes_read_so_html
            extracted_data['raw_preserved_block_2'] = f.read(remaining_bytes)
            
    except Exception as e:
        extracted_data['status'] = f"Footer Retention Error: {str(e)}"
        
    return extracted_data


def map_weights_to_vertex_groups(target_obj, weights, group_name):
    """
    Creates a dedicated Vertex Group on the mesh and maps an array 
    of 2,520 sequential weights directly to the vertex indices.
    """
    if not target_obj or target_obj.type != 'MESH':
        return False
        
    # Find or create the vertex group named after this weight channel section
    v_group = target_obj.vertex_groups.get(group_name)
    if not v_group:
        v_group = target_obj.vertex_groups.new(name=group_name)
        
    mesh_verts = target_obj.data.vertices
    
    # Assign each weight to its corresponding vertex index
    for idx, w_val in enumerate(weights):
        if idx < len(mesh_verts):
            # Only add non-zero influences to keep memory footprints clean
            if w_val > 0.0:
                v_group.add([idx], w_val, 'REPLACE')
                
    return True


def build_advanced_layer_mesh(parsed_msg, name="SWPM_Layer_Sec_60"):
    """
    Generates a visual mesh container for the layer points, applying 
    custom split normals and a viewport shader to colorize the 12 physics panels.
    """
    import bpy
    import random
    
    vertices = parsed_msg['vertices']
    normals = parsed_msg['normals']
    panels = parsed_msg['panels']
    
    if not vertices:
        return None
        
    mesh = bpy.data.meshes.new(name=name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    mesh.from_pydata(vertices, [], [])
    mesh.update()
    
    # 1. Bake Physics Panels to a Color Attribute Layer
    if panels and hasattr(mesh, "color_attributes"):
        color_layer = mesh.color_attributes.new(
            name="Physics_Panels", 
            type='BYTE_COLOR', 
            domain='POINT'
        )
        
        random.seed(42)
        panel_colors = []
        for _ in range(len(panels)):
            panel_colors.append((random.random(), random.random(), random.random(), 1.0))
            
        for panel in panels:
            p_idx = panel['panel_index']
            start = panel['vertex_start']
            count = panel['vertex_count']
            color = panel_colors[p_idx]
            
            for v_idx in range(start, start + count):
                if v_idx < len(color_layer.data):
                    color_layer.data[v_idx].color = color

    # 2. Build the Node-Based Preview Material
    mat_name = f"Mat_{name}_Preview"
    mat = bpy.data.materials.get(mat_name)
    if not mat:
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        
        # Clear default nodes
        nodes.clear()
        
        # Add Input Attribute, Shader, and Output
        node_attr = nodes.new(type='ShaderNodeAttribute')
        node_attr.attribute_name = "Physics_Panels"
        
        node_shader = nodes.new(type='ShaderNodeBsdfPrincipled')
        node_output = nodes.new(type='ShaderNodeOutputMaterial')
        
        # Connect Attribute color directly to Shader Base Color
        links.new(node_attr.outputs['Color'], node_shader.inputs['Base Color'])
        links.new(node_shader.outputs['BSDF'], node_output.inputs['Surface'])
        
    obj.data.materials.append(mat)

    # 3. Add a basic Geometry Nodes Modifier to force vertex sizing in the viewport
    geom_mod = obj.modifiers.new(name="Point_Viewport_Fix", type='NODES')
    # This keeps your manual geometry nodes tree intact but linked to the object
    
    # 4. Apply custom vector normals
    if normals and len(normals) >= len(vertices):
        #mesh.use_auto_smooth = True
        vert_norms = [normals[i] for i in range(len(vertices))]
        mesh.normals_split_custom_set_from_vertices(vert_norms)
        
    mesh.update()
    return obj

def parse_mesh_container_payload(f, block_size):
    """
    Decodes Sub-Blocks 1-8 from the 0x07B19A87 Mesh Container payload
    using dynamic stride assignments and layout boundaries.
    """
    extracted_data = {
        'vertices': [],
        'faces': [],
        'uvs': [],
        'vertex_colors': [],
        'normals': [],
        'skinning': [],
        'blendshape0_offsets': [],
        'blendshape1_offsets': [],
        'blend_skinning': [],
        'tangents': [],          # Added for Sub-Block 6
        'secondary_uvs': [],     # Added for Sub-Block 7
        'optimization_maps': []  # Added for Sub-Block 8
    }
    
    start_offset = f.tell()
    end_offset = start_offset + block_size
    
    # 1. Structural preamble
    f.read(4)  # Skip Base Block Start Marker (01 00 00 00)
    f.read(8)  # Skip initial spacer
    
    sub_block_index = 1
    while f.tell() < end_offset:
        current_sub_offset = f.tell()
        if current_sub_offset + 4 > end_offset:
            break
            
        # Read 4-byte payload size
        sub_length = struct.unpack("<I", f.read(4))[0]
        payload_start_offset = f.tell()
        next_sub_block = payload_start_offset + sub_length
        
        # [SUB-BLOCK 1: PACKED VERTEX COLOR + INT16 UV MAPS - Keeping your code]
        if sub_block_index == 1:
            num_elements = sub_length // 8
            print(f"\n[DEBUG SUB-BLOCK 1] Decoding Packed Color/UVs at 0x{payload_start_offset:X}. Count: {num_elements}")
            for _ in range(num_elements):
                color_bytes = f.read(4)
                r, g, b, a = struct.unpack("<4B", color_bytes)
                scaled_color = [r / 255.0, g / 255.0, b / 255.0, a / 255.0]
                extracted_data['vertex_colors'].append(scaled_color)
                
                raw_u, raw_v = struct.unpack("<2h", f.read(4))
                u = (raw_u / 8.0) / 256.0
                v = (256.0 - (raw_v / 8.0)) / 256.0
                extracted_data['uvs'].append((u, v))
            print(f"  -> Successfully unpacked {len(extracted_data['uvs'])} packed UV pairs and Colors.")

        # [SUB-BLOCK 2: PACKED XYZ VERTICES & NORMALS - Keeping your code]
        elif sub_block_index == 2:
            num_verts = sub_length // 12
            print(f"\n[DEBUG SUB-BLOCK 2] Decoding Packed Vertices/Normals at 0x{payload_start_offset:X}. Count: {num_verts}")
            for i in range(num_verts):
                raw_x, raw_y, raw_z, raw_nx, raw_ny, raw_nz = struct.unpack("<6h", f.read(12))
                pos_x = raw_x / 16384.0
                pos_y = raw_y / 16384.0
                pos_z = raw_z / 16384.0
                corrected_pos = mathutils.Vector((pos_x, -pos_z, pos_y))
                extracted_data['vertices'].append(corrected_pos)
                
                norm_x = raw_nx / 16384.0
                norm_y = raw_ny / 16384.0
                norm_z = raw_nz / 16384.0
                corrected_norm = mathutils.Vector((norm_x, -norm_z, norm_y))
                extracted_data['normals'].append(corrected_norm)
            print(f"  -> Successfully unpacked {len(extracted_data['vertices'])} positions and normals.")

        # [SUB-BLOCK 3: 8-INFLUENCE BONE INDICES & WEIGHTS - Keeping your code]
        elif sub_block_index == 3:
            num_elements = sub_length // 16
            print(f"\n[DEBUG SUB-BLOCK 3] Decoding 8-Byte Vertex Weights at 0x{payload_start_offset:X}. Count: {num_elements}")
            for i in range(num_elements):
                raw_data = struct.unpack("<8B8B", f.read(16))
                indices = raw_data[0:8]
                weights = raw_data[8:16]
                skin_entry = []
                for idx, weight in zip(indices, weights):
                    scaled_weight = weight / 255.0
                    if scaled_weight > 0.0:
                        skin_entry.append((idx, scaled_weight))
                extracted_data['skinning'].append(skin_entry)
            print(f"  -> Successfully unpacked {len(extracted_data['skinning'])} skinning records.")

        # [SUB-BLOCK 4: BLEND SHAPE VECTORS & SKINNING MASKS - Keeping your code]
        elif sub_block_index == 4:
            num_elements = sub_length // 48
            print(f"\n[DEBUG SUB-BLOCK 4] Decoding BlendShapes at 0x{payload_start_offset:X}. Count: {num_elements}")
            for i in range(num_elements):
                v_slice = f.read(48)
                bs0_x, bs0_y, bs0_z = struct.unpack("<3f", v_slice[0:12])
                extracted_data['blendshape0_offsets'].append(mathutils.Vector((bs0_x, -bs0_z, bs0_y)))
                
                bs1_x, bs1_y, bs1_z = struct.unpack("<3f", v_slice[12:24])
                extracted_data['blendshape1_offsets'].append(mathutils.Vector((bs1_x, -bs1_z, bs1_y)))
                
                mask_indices = struct.unpack("<8H", v_slice[24:40])
                mask_weights = struct.unpack("<8B", v_slice[40:48])
                skin_entry = []
                for idx, w_raw in zip(mask_indices, mask_weights):
                    w_float = w_raw / 255.0
                    if w_float > 0.0:
                        skin_entry.append((idx, w_float))
                extracted_data['blend_skinning'].append(skin_entry)
            print(f"  -> Successfully processed {len(extracted_data['blendshape0_offsets'])} morph states.")

        # ----------------------------------------------------
        # SUB-BLOCK 5: TRIANGLE FACE INDEX LIST - [Kept intact]
        # ----------------------------------------------------
        elif sub_block_index == 5:
            num_faces = sub_length // 6
            print(f"\n[DEBUG SUB-BLOCK 5] Decoding Faces at 0x{payload_start_offset:X}. Count: {num_faces}")
            for _ in range(num_faces):
                v1, v2, v3 = struct.unpack("<3H", f.read(6))
                extracted_data['faces'].append((v1, v2, v3))
            print(f"  -> Successfully unpacked {len(extracted_data['faces'])} Triangle indices.")

        # ----------------------------------------------------
        # SUB-BLOCK 6: CLUSTER DESCRIPTION DATA (ClusterDescData)
        # ----------------------------------------------------
        elif sub_block_index == 6:
            # 1. Read the cluster descriptor elements count
            #num_desc_elements_raw = f.read(4) 
            #num_desc_elements = struct.unpack("<I", num_desc_elements_raw)[0]
            # Correction here to use  sub_length
            num_desc_elements = sub_length
            
            print(f"\n[DEBUG SUB-BLOCK 6] Decoding ClusterDescData at 0x{payload_start_offset:X}. Count: {num_desc_elements}")
            
            # Read the 48 bytes of packed spatial bounding metadata
            # We calculate remaining space to read safely
            payload_bytes_to_read = sub_length
            extracted_data['cluster_desc_raw'] = f.read(payload_bytes_to_read)
            
            # Speculatively unpack the primary cluster spatial box parameters if data is present
            if len(extracted_data['cluster_desc_raw']) >= 24:
                cx, cy, cz = struct.unpack("<fff", extracted_data['cluster_desc_raw'][0:12])
                hx, hy, hz = struct.unpack("<fff", extracted_data['cluster_desc_raw'][12:24])
                print(f"  -> Bound Cluster 1 Center: ({cx:.4f}, {cy:.4f}, {cz:.4f})")
                print(f"  -> Bound Cluster 1 Extends: ({hx:.4f}, {hy:.4f}, {hz:.4f})")

        # ----------------------------------------------------
        # SUB-BLOCK 7: CLUSTER BITMASK ARRAY (ClusterBitMask)
        # ----------------------------------------------------
        elif sub_block_index == 7:
            # 1. Read the bitmask elements count header
            #num_mask_elements_raw = f.read(4)
            #num_mask_elements = struct.unpack("<I", num_mask_elements_raw)[0]
            # Correction here to use  sub_length
            num_mask_elements = sub_length
            
            print(f"\n[DEBUG SUB-BLOCK 7] Decoding ClusterBitMask at 0x{payload_start_offset:X}. Flags Count: {num_mask_elements}")
            
            # Read the remaining 48 bytes of bit alignment flags
            payload_bytes_to_read = sub_length
            extracted_data['cluster_bitmask_raw'] = f.read(payload_bytes_to_read)
            print(f"  -> Successfully cached {len(extracted_data['cluster_bitmask_raw'])} bytes of cluster routing bitmasks.")

        # ----------------------------------------------------
        # SUB-BLOCK 8: CLUSTER BOUNDING & INDEX TRAILER
        # ----------------------------------------------------
        elif sub_block_index == 8:
            # 1. Read the length indicator header (28 bytes)
            num_elements_raw = f.read(4)
            num_elements = struct.unpack("<I", num_elements_raw)[0]
            
            print(f"\n[DEBUG SUB-BLOCK 8] Decoding Cluster Index Trailer at 0x{payload_start_offset:X}. Length: {num_elements}")
            
            # 2. Extract Center and HalfExtends
            cx, cy, cz = struct.unpack("<3f", f.read(12))
            hx, hy, hz = struct.unpack("<3f", f.read(12))
            
            # Apply your established Blender coordinate correction layout (Y = -Z, Z = Y)
            mody_c, modz_c = -cz, cy
            mody_h, modz_h = -hz, hy
            
            extracted_data['cluster_center'] = (cx, mody_c, modz_c)
            extracted_data['cluster_half_extend'] = (hx, mody_h, modz_h)
            
            # 3. Extract Trailer Flags and Indices Counts
            unk_flag = struct.unpack("<B", f.read(1))[0]
            nb_face_indices = struct.unpack("<I", f.read(4))[0]
            termination_flag = struct.unpack("<B", f.read(1))[0]
            
            print(f"  -> Bounding Center: ({cx:.4f}, {cy:.4f}, {cz:.4f})")
            print(f"  -> Total Face Indices Managed: {nb_face_indices}")
            print(f"  -> Trailer Status Flag: {unk_flag}, Termination: {termination_flag}")


        else:
            f.read(sub_length)

            
        # Hard alignment enforcement safety check
        if f.tell() != next_sub_block:
            f.seek(next_sub_block)
            
        sub_block_index += 1
        
    return extracted_data


import bpy

def build_blender_mesh(mesh_data, mesh_name="Cloth_Mesh"):
    """
    Constructs a physical Blender Mesh Object from extracted 
    vertices, faces, and UV coordinates.
    """
    verts = mesh_data.get('vertices', [])
    faces = mesh_data.get('faces', [])
    uvs = mesh_data.get('uvs', [])
    
    if not verts or not faces:
        print("[ERROR] Cannot build mesh. Vertices or Faces list is completely empty.")
        return None
        
    print(f"\n[BLENDER MESH GENERATION] Building '{mesh_name}'...")
    
    # 1. Create a clean Mesh Asset container and a matching Viewport Object
    mesh_asset = bpy.data.meshes.new(name=f"{mesh_name}_Data")
    mesh_obj = bpy.data.objects.new(mesh_name, mesh_asset)
    
    # 2. Link the new object directly to the active scene collection
    bpy.context.scene.collection.objects.link(mesh_obj)
    
    # 3. Construct the primitive geometric structural topologies
    # This automatically assigns the 3379 vertices and 4482 faces safely
    mesh_asset.from_pydata(verts, [], faces)
    mesh_asset.update()
    
    print(f"  -> Geometry linked: {len(verts)} vertices, {len(faces)} faces.")
    
    # 4. Map the UV Layout texture coordinates if data is present
    if uvs:
        # Create a new UV Map layer inside the mesh asset data
        uv_layer = mesh_asset.uv_layers.new(name="UVMap")
        
        # Blender maps UVs per-loop (every corner index of every triangle face)
        # Iterate over every face, then over every corner index of that face
        uv_index = 0
        for loop in mesh_asset.loops:
            # Look up the vertex index this specific face corner relies on
            vertex_index = loop.vertex_index
            
            # Pull the pre-extracted UV coordinate pair matching that vertex index
            if vertex_index < len(uvs):
                u, v = uvs[vertex_index]
                # Assign the U, V values to the specific loop coordinate channel
                uv_layer.data[loop.index].uv = (u, v)
                
        print(f"  -> UV Layout mapped: {len(mesh_asset.loops)} loop coordinates pinned.")
        
    # 4b. Map Vertex Colors to the Face Corners (Loops) layer
    vertex_colors = mesh_data.get('vertex_colors', [])
    if vertex_colors:
        print(f"  -> Binding Vertex Colors to Face Corners...")
        
        # Create a new Color Attribute layer on the CORNER (Face Corner / Loop) domain
        # 'BYTE_COLOR' uses 8-bit sRGB format which matches the spreadsheet storage perfectly
        color_layer = mesh_asset.color_attributes.new(
            name="Color",
            type='BYTE_COLOR',
            domain='CORNER'
        )
        # Debug print out the vertex_colors for the first 4 vertices
        #vertcol = extracted_data.get('vertex_colors', [])
        for i in range(4):
            print(f"  -> vertex_colors:  {vertex_colors[i]}")
        
        # Loop through every face corner and map the corresponding vertex color
        for loop in mesh_asset.loops:
            vertex_index = loop.vertex_index
            if vertex_index < len(vertex_colors):
                # Blender colors expect an RGBA tuple/list (Red, Green, Blue, Alpha)
                color_rgba = vertex_colors[vertex_index]
                
                # Assign the color array directly into the loop data layer
                color_layer.data[loop.index].color = color_rgba
                
        print(f"  -> Color attributes linked: {len(mesh_asset.loops)} face corners colored.")

    # 4c. Map Custom Split Normals to the Face Corners (Loops) layer
    normals_data = mesh_data.get('normals', [])
    if normals_data:
        print(f"  -> Binding Custom Normals to Face Corners...")
        
        # Build an array containing a normal vector for every single Face Corner loop
        loop_normals = []
        for loop in mesh_asset.loops:
            vertex_index = loop.vertex_index
            if vertex_index < len(normals_data):
                # Grab the matching unscaled normal vector from Sub-Block 2
                norm_vec = normals_data[vertex_index]
                loop_normals.append(norm_vec)
            else:
                loop_normals.append(mathutils.Vector((0.0, 0.0, 1.0)))
                
        # In Blender 4.1+, assigning custom split normals automatically initializes
        # and locks them onto the face corners natively.
        mesh_asset.normals_split_custom_set(loop_normals)
        
        # Enable smooth shading on the mesh object so the custom normals evaluate correctly
        mesh_asset.shade_smooth()
        
        print(f"  -> Custom split normals linked: {len(loop_normals)} corner vectors applied.")
        
    # Apply Skeletal Skinning Weights to Vertex Groups
    skinning_data = mesh_data.get('skinning', [])
    if skinning_data:
        print("  -> Binding 8-influence weights to vertex groups...")
        
        # Look up the imported bone order from your active armature object
        skel_obj = bpy.data.objects.get("Skeleton")
        if skel_obj and skel_obj.type == 'ARMATURE':
            bone_names = [b.name for b in skel_obj.data.bones]
            
            for vert_idx, skin_entry in enumerate(skinning_data):
                for bone_idx, weight in skin_entry:
                    if bone_idx < len(bone_names):
                        group_name = bone_names[bone_idx]
                        
                        v_group = mesh_obj.vertex_groups.get(group_name)
                        if not v_group:
                            v_group = mesh_obj.vertex_groups.new(name=group_name)
                            
                        v_group.add([vert_idx], weight, 'REPLACE')
                        
            # Link the mesh to the skeleton using an Armature Modifier for real-time deformation
            arm_mod = mesh_obj.modifiers.new(name="ArmatureDeform", type='ARMATURE')
            arm_mod.object = skel_obj
            print("  -> Armature Modifier successfully attached to 'Cloth_Mesh'.")

    # 5b. Generate and Apply Morph Target Shape Keys (Fail-Safe Version)
    bs0_data = mesh_data.get('blendshape0_offsets', [])
    bs1_data = mesh_data.get('blendshape1_offsets', [])
    
    print(f"[DEBUG SHAPE KEYS] BS0 Count: {len(bs0_data)}, BS1 Count: {len(bs1_data)}")
    
    if bs0_data or bs1_data:
        print("  -> Initialising Shape Key layers on Cloth_Mesh...")
        
        # 1. Enforce a rigorous update of the mesh internal geometry arrays
        mesh_asset.update(calc_edges=True)
        
        # Verify the mesh contains the expected 3379 vertices before mapping indices
        num_mesh_verts = len(mesh_asset.vertices)
        print(f"  -> Blender Mesh internal vertex count: {num_mesh_verts}")
        
        if num_mesh_verts == 0:
            print("  [ERROR] Blender mesh geometry is uninitialized. Skipping shape keys.")
            return mesh_obj
            
        # 2. Create the absolute base reference shape layer
        base_shape = mesh_obj.shape_key_add(name="Basis", from_mix=False)
        #base_shape.user_of_id()
        
        # 3. Add BlendShape 0 (Target ID: 0xb836726c)
        if bs0_data:
            shape0 = mesh_obj.shape_key_add(name="BlendShape0_0xb836726c", from_mix=False)
            print("     [MAPPING] Injecting BlendShape0 vectors...")
            for v_idx, offset in enumerate(bs0_data):
                if v_idx < num_mesh_verts:
                    # Debug print the first 2 vectors in scientific notation to confirm data mapping
                    if v_idx < 2:
                        print(f"       * Vert [{v_idx}] Offset: X={offset.x:.4e}, Y={offset.y:.4e}, Z={offset.z:.4e}")
                    
                    shape0.data[v_idx].co = mesh_asset.vertices[v_idx].co + offset
                else:
                    print(f"       [WARNING] BS0 index {v_idx} out of mesh bounds ({num_mesh_verts}).")
                    break
                    
        # 4. Add BlendShape 1 (Target ID: 0x3de2a3a0)
        if bs1_data:
            shape1 = mesh_obj.shape_key_add(name="BlendShape1_0x3de2a3a0", from_mix=False)
            print("     [MAPPING] Injecting BlendShape1 vectors...")
            for v_idx, offset in enumerate(bs1_data):
                if v_idx < num_mesh_verts:
                    shape1.data[v_idx].co = mesh_asset.vertices[v_idx].co + offset
                else:
                    print(f"       [WARNING] BS1 index {v_idx} out of mesh bounds ({num_mesh_verts}).")
                    break
                    
        print("  -> Morph Shape Keys successfully injected into viewport object.")

    # 5c. Map Sub-Block 4 Corrective Blend Shape Skinning Masks
    blend_skinning_data = mesh_data.get('blend_skinning', [])
    if blend_skinning_data:
        print("  -> Initialising Secondary Shape Mask Vertex Groups...")
        
        # Pull your existing skeleton bone names to map indices correctly
        skel_obj = bpy.data.objects.get("Skeleton")
        bone_names = [b.name for b in skel_obj.data.bones] if (skel_obj and skel_obj.type == 'ARMATURE') else []
        
        for vert_idx, mask_entry in enumerate(blend_skinning_data):
            for bone_idx, weight in mask_entry:
                # 1. Resolve the target bone name
                if bone_names and bone_idx < len(bone_names):
                    base_bone_name = bone_names[bone_idx]
                else:
                    base_bone_name = f"Bone_{bone_idx}"
                
                # 2. Use a unique suffix prefix to keep these isolated from standard rigging
                # This creates groups like "Mask_Joint05", preventing data overrides
                mask_group_name = f"Mask_{base_bone_name}"
                
                # 3. Create or fetch the secondary group container
                m_group = mesh_obj.vertex_groups.get(mask_group_name)
                if not m_group:
                    m_group = mesh_obj.vertex_groups.new(name=mask_group_name)
                    
                # 4. Assign the weight entry cleanly
                m_group.add([vert_idx], weight, 'REPLACE')
                
        print(f"  -> Successfully generated secondary mask groups.")

    
    # 5. Refresh the scene boundaries and select the final mesh
    bpy.context.view_layer.objects.active = mesh_obj
    mesh_obj.select_set(True)
    
    print(f"[BLENDER MESH GENERATION] Mesh '{mesh_name}' built and displayed successfully.")
    return mesh_obj


def add_bone_to_skeleton(bone_info):
    if "Deform Bones" in bpy.data.collections:
        collection = bpy.data.collections["Deform Bones"]
    else:
        collection = bpy.data.collections.new("Deform Bones")
        bpy.context.scene.collection.children.link(collection)
        
    if "Skeleton" in bpy.data.objects:
        skel_obj = bpy.data.objects["Skeleton"]
        arm_data = skel_obj.data
    else:
        arm_data = bpy.data.armatures.new("Skeleton_Data")
        skel_obj = bpy.data.objects.new("Skeleton", arm_data)
        collection.objects.link(skel_obj)
        
    bpy.context.view_layer.objects.active = skel_obj
    bpy.ops.object.mode_set(mode='EDIT')
    
    bone_name = bone_info['name']
    m = bone_info['matrix']
    
    # 1. Build the initial matrix container from raw sequential floats
    matrix_4x4 = mathutils.Matrix([
        [m[0],  m[1],  m[2],  m[3]],
        [m[4],  m[5],  m[6],  m[7]],
        [m[8],  m[9],  m[10], m[11]],
        [m[12], m[13], m[14], m[15]]
    ])
    
    # 2. Transpose it to swap Row-Major (C#) into Column-Major (Blender)
    matrix_4x4.transpose()
    
    # 3. Apply the inversion step requested by the C# engine logic
    try:
        matrix_4x4 = matrix_4x4.inverted()
    except ValueError:
        print(f"Warning: Matrix for bone '{bone_name}' is singular.")
        matrix_4x4 = mathutils.Matrix.Identity(4)
    
    edit_bone = arm_data.edit_bones.new(bone_name)
    
    # 4. Now assign the fully compliant matrix to the EditBone use either scaled or unscaled
    edit_bone.matrix = matrix_4x4     #Unscaled option
    #edit_bone.matrix = blender_bone_matrix       #Scaled option
    
    # 5. Extract the correctly mapped translation vector
    bone_origin = matrix_4x4.to_translation()
    
    # Apply your working coordinate orientation correction to the origin
    temp_y = bone_origin.y
    temp_z = bone_origin.z
    bone_origin.y = -temp_z
    bone_origin.z = temp_y
    
    # 6. Explicitly enforce the head position in 3D scene space
    edit_bone.head = bone_origin

    # --- CALCULATE TRUE VECTOR LENGTH AND DIRECTION ---
    # Extract the forward direction vector from the bone's rotation matrix (Y-Axis)
    forward_dir = matrix_4x4.to_3x3().col[1].normalized()
    
    # Apply the exact same coordinate orientation correction to the direction vector
    dir_y = forward_dir.y
    dir_z = forward_dir.z
    forward_dir.y = -dir_z
    forward_dir.z = dir_y
    
    # Calculate the true scale/length factor from the matrix transformsn
    # This is the square root of the sum of squares of the matrix scale channels
    scale_channels = matrix_4x4.to_scale()
    import math
    true_length = math.sqrt(edit_bone.head.x**2 + edit_bone.head.y**2 + edit_bone.head.z**2)
    #true_length = math.sqrt(scale_channels.x**2 + scale_channels.y**2 + scale_channels.z**2)
    #print(f"scalechannels = {scale_channels.x}, {scale_channels.y}, {scale_channels.z}")
    
    # Fallback to a small default size if the matrix scaling calculates to zero
    if true_length < 0.001:
        true_length = 0.1
        
    # Project the tail away from the head using the true calculated length
    edit_bone.tail = bone_origin + (forward_dir * true_length)
    print(f"bone roll = {edit_bone.roll}")
    edit_bone.roll = edit_bone.roll - math.radians(156) #to flip
    print(f"bone roll modif = {edit_bone.roll}")

    bpy.ops.object.mode_set(mode='OBJECT')


def process_section_by_index(idx):
    addr, sec_num, sec_type, size = AnvilState.sections_map[idx]
    marker_name = MARKERS[sec_type]
    
    print("--------------------------------------------------")
    print("PROCESSING SECTION: " + str(idx + 1))
    print("Address: 0x" + f"{addr:X}")
    print("Type: " + marker_name)
    
    with open(AnvilState.file_path, MODE_RB) as f:
        f.seek(addr + 12) 
        if sec_type == 0x9EF0E7A1: 
            msg = parse_deform_bone_payload(f, size)
            add_bone_to_skeleton(AnvilState.deform_bones_data[-1])
            print("Result: " + msg)
        elif sec_type == 0xA57387EF:
            msg = parse_primitive_payload(f)
            print("Result: " + msg)
        elif sec_type == 0x0B1D34C1:
            msg = parse_material_payload(f)
            print("Result: " + msg)
        elif sec_type == 0x92E29AB6:
            # Safely store the catalog hashes globally or in a layout container
            context_blendshape_ids = parse_section_53_blendshape_list(f, size)
        elif sec_type == 0x07B19A87:
            msg = parse_mesh_container_payload(f, size)
            print(f"Result: Vertices={len(msg['vertices'])}, Faces={len(msg['faces'])}, UVs={len(msg['uvs'])}")
            # Trigger the generation of the cloth object
            cloth_obj = build_blender_mesh(msg, "Cloth_Mesh")
        elif sec_type == 0x891A367C:
            msg = parse_section_891A367C(f, size)
            print(f"Result: Vertices={len(msg['vertices'])}, SWPM Targets={msg['target_count']}, Status={msg['status']}")
            
            # Optional: If you want to see them in Blender visually
            #if msg['vertices']:
                #build_proxy_point_cloud(msg['vertices'], f"SWPM_Proxy_Sec_{idx+1}")
            if msg['vertices']:
                proxy_name = f"SWPM_Proxy_Sec_{idx+1}"
                # Save explicitly back to your class container tracking property
                AnvilState.active_proxy_obj = build_proxy_point_cloud(msg['vertices'], proxy_name)
                
        elif sec_type == 0xC2023DA2:
            msg = parse_section_C2023DA2(f, size)
            print(f"SWPMTarget: ID=0x{msg['target_id']:08X}, Extracted Vectors={len(msg['vectors'])}, Status={msg['status']}")

            # Hook the parsed shapes straight into the Section 55 mesh container
            if msg['vectors'] and getattr(AnvilState, 'active_proxy_obj', None):
                key_label = f"Target_0x{msg['target_id']:08X}_Sec_{idx+1}"
                success = apply_swpm_shape_key(AnvilState.active_proxy_obj, msg['vectors'], key_label)
                if success:
                    print(f"   -> Successfully baked as Shape Key: {key_label}")
                    
        elif sec_type == 0xFD4C3871:
            msg = parse_section_FD4C3871(f, size)

            # Optional: Build the visual layer point cloud in Blender to inspect it
            #if msg['vertices']:
            #    build_proxy_point_cloud(msg['vertices'], f"SWPM_Layer_Sec_{idx+1}")
            
            # Generate the advanced visual checking container
            if msg['vertices']:
                build_advanced_layer_mesh(msg, f"SWPM_Layer_Sec_{idx+1}")
            
            print(f"SkinWrapLayerMesh: Extracted Vertices={len(msg['vertices'])}, Normals={len(msg['normals'])}")
            print(f"   -> Physics Panels Decoded: {len(msg['panels'])} zones found.")
            for panel in msg['panels'][:3]: # Print first 3 panels as verification
                print(f"      * Zone {panel['panel_index']}: StartIdx={panel['vertex_start']}, Count={panel['vertex_count']}")
                
        elif sec_type == 0x3FD52D67:
            msg = parse_section_3FD52D67(f, size)
            print(f"SWLMPWIndices (Sec {idx+1}): Block1_Size={msg['sub_block_1_size']}B, Block2_Size={msg['sub_block_2_size']}B, Status={msg['status']}")
        
        elif sec_type == 0xC5B003DC:
            msg = parse_section_C5B003DC(f, size)
            print(f"LayerMeshWeights (Sec {idx+1}): Extracted Weights={len(msg['weights'])}, Status={msg['status']}")
            
            # Map the parsed weights back to the parent point cloud container
            # Looks for the active object we instantiated back in Section 60
            active_layer_mesh = bpy.data.objects.get("SWPM_Layer_Sec_60")
            if msg['weights'] and active_layer_mesh:
                g_label = f"Weight_Channel_Sec_{idx+1}"
                success = map_weights_to_vertex_groups(active_layer_mesh, msg['weights'], g_label)
                if success:
                    print(f"   -> Successfully mapped to Vertex Group: {g_label}")

        elif sec_type == 0xFC9E1595:
            # Section 77: Empty / Synchronization Marker
            # Simply flush out any remaining bytes matching the size boundary
            if size > 0:
                f.read(size)
            print(f"Section {idx+1} (0xFC9E1595): Empty Marker Passthrough.")
            
        elif sec_type == 0xC351EE43:
            msg = parse_section_C351EE43(f, size)
            print(f"MeshDescriptor (Sec {idx+1}): Strides [S={msg['stride_static']}, D={msg['stride_dynamic']}, W={msg['stride_weights']}]")
            print(f"   -> Bounding Box Center: {[round(c, 4) for c in msg['center']]}, HalfExtends: {[round(h, 4) for h in msg['half_extend']]}")

        elif sec_type == 0x0645ABB5:
            msg = parse_section_0645ABB5(f, size)
            print(f"LayoutBlueprint (Sec {idx+1}): Strides [Static={msg['stride_static']}, Dynamic={msg['stride_dynamic']}, Precompute={msg['stride_precompute']}]")
            print(f"   -> Quantities: Bones/Vert={msg['bones_per_vertex']}, BlendShapes={msg['blendshapes_qty']}, SkinWrapWeights={msg['skinwrap_weight_qty']}")

        elif sec_type == 0xA57387EF:
            msg = parse_section_A57387EF(f, size)
            print(f"GeometryAllocator (Sec {idx+1}): Total Vertices={msg['total_vertices']}, Total Faces={msg['total_faces']}")
            print(f"   -> Drawing Clusters Allocated: {msg['cluster_count']}, Status={msg['status']}")
            
        elif sec_type == 0x0B1D34C1:
            msg = parse_section_0B1D34C1(f, size)
            print(f"FileFooter (Sec {idx+1}): Target Mesh Vertices Verification={msg['total_vertices']}")
            print(f"   -> Material Binding Key: 0x{msg['material_id_1']:016X}")
            print(f"   -> Preserved Data Blocks: Buffer1={len(msg['raw_preserved_block_1'])}B, Buffer2={len(msg['raw_preserved_block_2'])}B")
            print(f"=== REVERSE ENGINEERING COMPLETED SUCCESSFULLY ===")

        else:
            print("Result: Skipped payload processing")
    print("--------------------------------------------------")

def debug_print_sections_map():
    """
    Prints a cleanly formatted structural overview of the cached AnvilState sections map
    for binary verification against expected structural boundaries.
    """
    if not hasattr(AnvilState, 'sections_map') or not AnvilState.sections_map:
        print("\n[DIAGNOSTIC ERROR] AnvilState.sections_map is empty or uninitialized!")
        return

    print("\n======================================================================")
    print(f"DIAGNOSTIC BLOCK: VERIFYING ANVIL_STATE SECTIONS MAP")
    print(f"Total Sections Cached: {len(AnvilState.sections_map)}")
    print("======================================================================")
    print(f"{'Idx':<5} | {'Hex Address':<12} | {'Sec Num':<8} | {'Type ID (Hex)':<14} | {'Payload Size (Bytes)'}")
    print("-" * 70)
    
    for i, section in enumerate(AnvilState.sections_map):
        addr, sec_num, sec_type, size = section
        # Format variables for crisp terminal spacing alignment
        hex_addr = f"0x{addr:X}"
        hex_type = f"0x{sec_type:08X}"
        
        print(f"{i+1:<5} | {hex_addr:<12} | {sec_num:<8} | {hex_type:<14} | {size:,}")
        
    print("======================================================================\n")

class ANVIL_OT_InitializeFile(bpy.types.Operator):
    bl_idname = "anvil.init_file"
    bl_label = "Initialize and Map Layout File"
    
    def execute(self, context):
        os.system('cls' if os.name == 'nt' else 'clear')
        clear_scene_tree()
        AnvilState.sections_map.clear()
        AnvilState.deform_bones_data.clear()
        AnvilState.current_index = -1
        
        if not os.path.exists(AnvilState.file_path):
            self.report({'ERROR'}, "File missing at target path")
            return {'CANCELLED'}
            
        with open(AnvilState.file_path, MODE_RB) as f:
            file_size = os.path.getsize(AnvilState.file_path)
            
            start_ind_tup = struct.unpack(FMT_UINT16, f.read(2))
            file_id = struct.unpack(FMT_UINT64, f.read(8))[0]
            file_type = struct.unpack(FMT_UINT32, f.read(4))[0]
            
            f.read(15) 
            num_bones = struct.unpack(FMT_UINT8, f.read(1))[0]
            check_zero_tup = struct.unpack(FMT_UINT32, f.read(4))
            
            print("==================================================")
            print("HEADER INTERPRETATION SUMMARY")
            print("==================================================")
            print("File ID: " + str(file_id))
            print("File Type: 0x" + f"{file_type:08X}")
            print("Number of Bones: " + str(num_bones))
            print("==================================================")
            
            f.seek(33)
            temp_map = []
            while f.tell() <= file_size - 12:
                addr = f.tell()
                sec_num = struct.unpack(FMT_UINT32, f.read(4))[0]
                sec_zero_tup = struct.unpack(FMT_UINT32, f.read(4))
                sec_type = struct.unpack(FMT_UINT32, f.read(4))[0]
                
                if sec_type in MARKERS:
                    temp_map.append((addr, sec_num, sec_type))
                else:
                    f.seek(addr + 1)
            
            for i, (addr, sec_num, sec_type) in enumerate(temp_map):
                if i < len(temp_map) - 1:
                    payload_size = temp_map[i+1][0] - (addr + 12)
                else:
                    payload_size = file_size - (addr + 12)
                AnvilState.sections_map.append(
                    (addr, sec_num, sec_type, payload_size)
                )
                
        AnvilState.current_index = 0
        self.report({'INFO'}, "Mapped sections successfully.")
        return {'FINISHED'}

class ANVIL_OT_RunContinuous(bpy.types.Operator):
    bl_idname = "anvil.run_continuous"
    bl_label = "Run to End"
    
    def execute(self, context):
        start_idx = AnvilState.current_index
        total_count = len(AnvilState.sections_map)
        if start_idx < 0 or start_idx >= total_count:
            self.report({'WARNING'}, "No remaining sections.")
            return {'CANCELLED'}
            
        print(">>> CONTINUOUS LOOP RUNNING TO END <<<")
        for idx in range(start_idx, total_count):
            process_section_by_index(idx)
            
        AnvilState.current_index = total_count
        self.report({'INFO'}, "Continuous execution finished.")
        return {'FINISHED'}
    
import os
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty
from bpy.types import Operator

class IMPORT_OT_anvil_mesh(Operator, ImportHelper):
    """Import an AnvilSoft Mesh File"""
    bl_idname = "import_mesh.anvil_soft"
    bl_label = "Import AnvilSoft Mesh"
    bl_options = {'PRESET', 'UNDO'}
    print(f"Test1 -----------------")
    # Restrict file selection window to strictly show .Mesh files
    filename_ext = ".Mesh"
    filter_glob: StringProperty(
        default="*.Mesh",
        options={'HIDDEN'},
        maxlen=255,
    )

    def execute(self, context):
        # 1. Grab the path selected by the user in the browser window
        file_path = self.filepath
        AnvilState.file_path = file_path
        
        if not os.path.exists(file_path):
            self.report({'ERROR'}, f"File not found: {file_path}")
            return {'CANCELLED'}
            
        print(f"\n[START IMPORT] Selected File: {file_path}")
        
        # 2. Call your existing main master file-reading workflow function here
        # Make sure this matches whatever function name runs your 81 sections!
        try:
            # Assuming your master executor is named process_sections(file_path)
            # Adjust the function name below to match your exact script structure:
            with open(file_path, "rb") as f:
                # Add your core processing master index loop logic here
                # e.g., process_sections_from_file(f)
                try:
                    try:
                        ANVIL_OT_InitializeFile.execute(self, context)
                        bpy.utils.unregister_class(ANVIL_OT_InitializeFile)
                    except Exception:
                        pass
                    bpy.utils.register_class(ANVIL_OT_InitializeFile)
                    try:
                        ANVIL_OT_RunContinuous.execute(self, context)
                        bpy.utils.unregister_class(ANVIL_OT_RunContinuous)
                    except Exception:
                        pass 
                    bpy.utils.register_class(ANVIL_OT_RunContinuous)
                except RuntimeError:
                    pass 
                pass
            
            # Trigger the diagnostic dump
            debug_print_sections_map()
            
            self.report({'INFO'}, f"Successfully imported: {os.path.basename(file_path)}")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Import failed: {str(e)}")
            return {'CANCELLED'}


# -------------------------------------------------------------------
# Registration Layer (Creates the actual UI button mechanism)
# -------------------------------------------------------------------
def menu_func_import(self, context):
    self.layout.operator(IMPORT_OT_anvil_mesh.bl_idname, text="AnvilSoft Mesh (.Mesh)")

def register_importer_menu():
    # 1. Clean slate check: Unregister class first if it exists
    try:
        bpy.utils.unregister_class(IMPORT_OT_anvil_mesh)
    except Exception:
        pass
        
    # 2. ACCURATE PURGE MECHANISM: Look inside Blender's dynamic UI initialization cache
    # This fetches all registered extensions tracking the TOPBAR menu hooks.
    if hasattr(bpy.types.TOPBAR_MT_file_import, "_dyn_ui_initialize"):
        try:
            # Safely extract dynamic list instances matching your draw function name
            dyn_funcs = bpy.types.TOPBAR_MT_file_import._dyn_ui_initialize()
            for func in list(dyn_funcs):
                if hasattr(func, "__name__") and func.__name__ == "menu_func_import":
                    bpy.types.TOPBAR_MT_file_import.remove(func)
        except Exception:
            pass
    # Secondary flat lookup check if anything managed to slip through
    try:
        bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    except Exception:
        pass
    print(f"Test3 ------------------")

    # 3. Freshly register the class and append EXACTLY ONE clean menu item
    bpy.utils.register_class(IMPORT_OT_anvil_mesh)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister_importer_menu():
    try:
        bpy.utils.unregister_class(IMPORT_OT_anvil_mesh)
    except Exception:
        pass
        
    if hasattr(bpy.types.TOPBAR_MT_file_import, "_dyn_ui_initialize"):
        try:
            dyn_funcs = bpy.types.TOPBAR_MT_file_import._dyn_ui_initialize()
            for func in list(dyn_funcs):
                if hasattr(func, "__name__") and func.__name__ == "menu_func_import":
                    bpy.types.TOPBAR_MT_file_import.remove(func)
        except Exception:
            pass

import bpy
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty
import os

def pack_vertex_static_stream(blender_mesh, blender_obj):
    """
    Packs vertex colors and UV map coordinates back into an 8-byte 
    Sub-Block 1 compressed data stream structure.
    Adds type-safety guards to prevent reading boolean/non-color attributes.
    """
    import struct
    
    packed_buffer = b""
    num_verts = len(blender_mesh.vertices)
    
    # 1. Safely find a valid Color Layer (ignore boolean/weight selection masks)
    color_layer = None
    if blender_mesh.color_attributes:
        # Check if the active one is a valid color format
        active_attr = blender_mesh.color_attributes.active
        if active_attr and active_attr.data_type in {'COLOR', 'BYTE_COLOR'}:
            color_layer = active_attr
        else:
            # Look for any layer that actually contains color data
            for attr in blender_mesh.color_attributes:
                if attr.data_type in {'COLOR', 'BYTE_COLOR'}:
                    color_layer = attr
                    break
        
    # 2. Fetch active UV Mapping layer data
    uv_layer = blender_mesh.uv_layers.active
    
    # Pre-allocate array containers to match absolute vertex limits cleanly
    vert_uvs = [(0.0, 0.0)] * num_verts
    # Default to solid white opaque colors (255, 255, 255, 255)
    vert_colors = [[255, 255, 255, 255] for _ in range(num_verts)]
    
    # Explicitly enumerate loops to map loops back to clean vertex indices
    if uv_layer or color_layer:
        for loop_idx, loop in enumerate(blender_mesh.loops):
            v_idx = loop.vertex_index
            
            if uv_layer and loop_idx < len(uv_layer.data):
                vert_uvs[v_idx] = uv_layer.data[loop_idx].uv
                
            if color_layer and loop_idx < len(color_layer.data):
                c_val = color_layer.data[loop_idx].color
                # Convert the color components safely
                vert_colors[v_idx] = [
                    int(max(0.0, min(1.0, c_val[0])) * 255),
                    int(max(0.0, min(1.0, c_val[1])) * 255),
                    int(max(0.0, min(1.0, c_val[2])) * 255),
                    int(max(0.0, min(1.0, c_val[3])) * 255) if len(c_val) > 3 else 255
                ]
            
    # Serialize the array entries sequentially matching engine formats
    for v_idx in range(num_verts):
        r, g, b, a = vert_colors[v_idx]
        u, v = vert_uvs[v_idx]
        
        # Invert the precision float layout back to compact signed shorts
        raw_u = int(round(u * 256.0 * 8.0))
        raw_v = int(round(256.0 - (v * 256.0)) * 8.0)
        
        # Safeguard structural overflow bounds limits safely (-32768 to 32767)
        raw_u = max(-32768, min(32767, raw_u))
        raw_v = max(-32768, min(32767, raw_v))
        
        packed_buffer += struct.pack("<4B2h", r, g, b, a, raw_u, raw_v)
        
    return packed_buffer


def pack_mesh_triangle_faces(blender_mesh):
    """
    Serializes Blender face polygon loop sequences into 6-byte 
    unsigned Int16 structural indices (Sub-Block 5).
    """
    import struct
    
    packed_buffer = b""
    
    # Loop through each individual triangle face asset element structure
    for face in blender_mesh.polygons:
        if len(face.vertices) == 3:
            v1, v2, v3 = face.vertices
            packed_buffer += struct.pack("<3H", v1, v2, v3)
            
    return packed_buffer

def pack_vertex_dynamic_stream(blender_mesh):
    """
    Inverts Blender's axes layout transformations and packs XYZ metrics 
    back into 12-byte signed Int16 array structures.
    """
    import struct
    import mathutils
    
    packed_buffer = b""
    
    for vertex in blender_mesh.vertices:
        # 1. Isolate structural spatial position elements
        bx, by, bz = vertex.co
        
        # 2. Reverse the coordinate mapping matrix axes adjustments (Blender -> Game Engine)
        # Main mapping matrix flip inversion layout rule:
        engine_x = bx
        engine_y = bz
        engine_z = -by
        
        # 3. Scale back to fixed-point Int16 boundaries (* 16384.0)
        raw_x = int(round(engine_x * 16384.0))
        raw_y = int(round(engine_y * 16384.0))
        raw_z = int(round(engine_z * 16384.0))
        
        # Clamp values safely inside short limits (-32768 to 32767) to prevent overflow
        raw_x = max(-32768, min(32767, raw_x))
        raw_y = max(-32768, min(32767, raw_y))
        raw_z = max(-32768, min(32767, raw_z))
        
        # 4. Handle Normals allocation mapping alignment adjustments correspondingly
        bnx, bny, bnz = vertex.normal
        engine_nx = bnx
        engine_ny = bnz
        engine_nz = -bny
        
        raw_nx = max(-32768, min(32767, int(round(engine_nx * 16384.0))))
        raw_ny = max(-32768, min(32767, int(round(engine_ny * 16384.0))))
        raw_nz = max(-32768, min(32767, int(round(engine_nz * 16384.0))))
        
        # Pack 6 short variables (12 Bytes Total per element stride)
        packed_buffer += struct.pack("<6h", raw_x, raw_y, raw_z, raw_nx, raw_ny, raw_nz)
        
    return packed_buffer

def perform_anvil_binary_injection(template_path, output_path, blender_obj):
    """
    Dynamic topology injection engine.
    Supports structural addition/deletion of vertices and faces by dynamically 
    recalculating inner strides and updating all downstream global metadata counters.
    """
    import struct
    import os
    
    if not hasattr(AnvilState, 'sections_map') or not AnvilState.sections_map:
        print("Error: AnvilState section tracking data map is missing or uninitialized.")
        return False
        
    try:
        blender_mesh = blender_obj.data
        
        # 1. Gather live topology metrics straight from Blender's active workspace
        new_vertex_count = len(blender_mesh.vertices) 
        new_face_count = len(blender_mesh.polygons)
        new_face_indices_count = new_face_count * 3
        
        print(f"\n[TOPOLOGY ADJUSTMENT] Serializing: {new_vertex_count} vertices, {new_face_count} faces.")
        
        # 2. Pack live topology elements into raw binary streams
        updated_sb1_uv_color = pack_vertex_static_stream(blender_mesh, blender_obj)
        updated_sb5_triangle = pack_mesh_triangle_faces(blender_mesh)
        
        with open(template_path, "rb") as f_src, open(output_path, "wb") as f_dst:
            
            # Preserve the global 33-byte unmodded file preamble header exactly
            first_section_addr = AnvilState.sections_map[0][0]
            if first_section_addr > 0:
                f_src.seek(0)
                f_dst.write(f_src.read(first_section_addr))
            
            for idx, section_data in enumerate(AnvilState.sections_map):
                addr, sec_num, sec_type, size = section_data
                
                # ====================================================================
                # ?? LAYER 1: MAIN CLOTH MESH INJECTION (SECTION 79: 0x07B19A87)
                # ====================================================================
                if sec_type == 0x07B19A87:
                    print(f"   -> [TWEAK] Injecting mesh elements into Section {idx + 1}...")
                    
                    f_src.seek(addr)
                    header_bytes = f_src.read(12)
                    preamble_bytes = f_src.read(12)
                    f_dst.write(header_bytes)
                    f_dst.write(preamble_bytes)
                    
                    # Skip old Sub-Block 1
                    sb1_size_old = struct.unpack("<I", f_src.read(4))[0]
                    f_src.seek(f_src.tell() + sb1_size_old)
                    
                    # Skip old Sub-Block 2, but grab a 6-byte shading template token
                    sb2_size_old = struct.unpack("<I", f_src.read(4))[0]
                    sample_vert = f_src.read(12)
                    default_trailer_token = sample_vert[6:12] 
                    f_src.seek(f_src.tell() + sb2_size_old - 12)
                    
                    # Read and retain Sub-Block 3 & 4 exactly
                    sb3_size_raw = f_src.read(4)
                    sb3_size = struct.unpack("<I", sb3_size_raw)[0]
                    sb3_data = f_src.read(sb3_size)
                    
                    sb4_size_raw = f_src.read(4)
                    sb4_size = struct.unpack("<I", sb4_size_raw)[0]
                    sb4_data = f_src.read(sb4_size)
                    
                    # Skip old face array indexing (Sub-Block 5)
                    sb5_size_old = struct.unpack("<I", f_src.read(4))[0]
                    f_src.seek(f_src.tell() + sb5_size_old)
                    
                    # Read Sub-Blocks 6 & 7 exactly (Cluster Descriptors)
                    sb6_size_raw = f_src.read(4)
                    sb6_size = struct.unpack("<I", sb6_size_raw)[0]
                    sb6_data = f_src.read(sb6_size)
                    
                    sb7_size_raw = f_src.read(4)
                    sb7_size = struct.unpack("<I", sb7_size_raw)[0]
                    sb7_data = f_src.read(sb7_size)
                    
                    # Parse and update Sub-Block 8 dynamically to inject the new NbFaceIndices count
                    sb8_size_raw = f_src.read(4)
                    sb8_size = struct.unpack("<I", sb8_size_raw)[0]
                    sb8_payload_length = struct.unpack("<I", f_src.read(4))[0]
                    
                    # Read original Center, Extends, and active configurations
                    cx, cy, cz = struct.unpack("<3f", f_src.read(12))
                    hx, hy, hz = struct.unpack("<3f", f_src.read(12))
                    unk_flag = f_src.read(1)
                    
                    f_src.read(4) # Skip out the old outdated face index count value
                    termination_flag = f_src.read(1)
                    
                    # Recompile Sub-Block 8 with our updated face index value
                    updated_sb8_payload = (
                        struct.pack("<3f", cx, cy, cz) +
                        struct.pack("<3f", hx, hy, hz) +
                        unk_flag +
                        struct.pack("<I", new_face_indices_count) + # INJECTED COUNTER
                        termination_flag
                    )
                    
                    # --- BUILD THE NEW SUB-BLOCK 2 POSITION ARRAY ---
                    updated_sb2_buffer = b""
                    for v_idx in range(new_vertex_count):
                        bx, by, bz = blender_mesh.vertices[v_idx].co
                        engine_x = bx
                        engine_y = bz
                        engine_z = -by
                        
                        raw_x = max(-32768, min(32767, int(round(engine_x * 16384.0))))
                        raw_y = max(-32768, min(32767, int(round(engine_y * 16384.0))))
                        raw_z = max(-32768, min(32767, int(round(engine_z * 16384.0))))
                        
                        original_vert_offset = addr + 12 + 12 + 4 + sb1_size_old + 4 + (v_idx * 12)
                        if original_vert_offset < (addr + 12 + size - sb8_size - sb7_size - sb6_size):
                            current_src_pos = f_src.tell()
                            f_src.seek(original_vert_offset + 6) 
                            preserved_shading_bytes = f_src.read(6)
                            f_src.seek(current_src_pos) 
                        else:
                            preserved_shading_bytes = default_trailer_token
                        
                        updated_sb2_buffer += struct.pack("<3h", raw_x, raw_y, raw_z) + preserved_shading_bytes
                    
                    # --- COMPUTE TOTAL MODIFIED BOUNDARIES ---
                    len_sb1 = len(updated_sb1_uv_color)
                    len_sb2 = len(updated_sb2_buffer)
                    len_sb5 = len(updated_sb5_triangle)
                    len_sb8 = len(updated_sb8_payload)
                    
                    # Write all sub-blocks sequentially
                    f_dst.write(struct.pack("<I", len_sb1))
                    f_dst.write(updated_sb1_uv_color)
                    f_dst.write(struct.pack("<I", len_sb2))
                    f_dst.write(updated_sb2_buffer)
                    f_dst.write(sb3_size_raw + sb3_data)
                    f_dst.write(sb4_size_raw + sb4_data)
                    f_dst.write(struct.pack("<I", len_sb5))
                    f_dst.write(updated_sb5_triangle)
                    f_dst.write(sb6_size_raw + sb6_data)
                    f_dst.write(sb7_size_raw + sb7_data)
                    
                    # Write updated Sub-Block 8
                    f_dst.write(sb8_size_raw)
                    f_dst.write(struct.pack("<I", len_sb8))
                    f_dst.write(updated_sb8_payload)
                    
                # ====================================================================
                # ?? LAYER 2: GLOBAL MESH ALLOCATOR INJECTION (SECTION 81: 0xA57387EF)
                # ====================================================================
                elif sec_type == 0xA57387EF:
                    print(f"   -> [METADATA] Updating Global Inventory Counters in Section {idx + 1}...")
                    f_src.seek(addr)
                    header_bytes = f_src.read(12)
                    f_dst.write(header_bytes)
                    
                    f_src.read(8) # Pass initial padding spacers
                    f_dst.write(struct.pack("<II", 0, 0)) # Write spacers intact
                    
                    f_src.read(2) # Skip old TotalVertices value
                    #f_dst.write(struct.pack("<I", new_vertex_count)) # INJECTED COUNTER
                    # Little-endian, unsigned short (2 bytes)
                    f_dst.write(struct.pack("<H", new_vertex_count))
                    
                    f_dst.write(f_src.read(6)) # Pass layout spacer through intact
                    
                    f_src.read(2) # Skip old TotalFaces value
                    #f_dst.write(struct.pack("<I", new_face_count)) # INJECTED COUNTER
                    # Little-endian, unsigned short (2 bytes)
                    f_dst.write(struct.pack("<H", new_face_count))

                    
                    # Copy over whatever remains inside the allocation chunk footprint boundaries
                    remaining_sec_size = size - (8 + 4 + 4 + 4 + 2)
                    f_dst.write(f_src.read(remaining_sec_size))
                    
                # ====================================================================
                # ?? LAYER 3: FILE SERIALIZATION FOOTER INJECTION (SECTION 82: 0x0B1D34C1)
                # ====================================================================
                elif sec_type == 0x0B1D34C1:
                    print(f"   -> [FOOTER] Updating Final Verification Limits in Section {idx + 1}...")
                    f_src.seek(addr)
                    header_bytes = f_src.read(12)
                    f_dst.write(header_bytes)
                    
                    f_dst.write(f_src.read(5)) # Copy early preamble tokens intact
                    f_src.read(2) # Skip old TotalVertices U16 value slot
                    f_dst.write(struct.pack("<H", new_vertex_count)) # INJECTED COUNTER
                    # Flush the final trailing metadata/material hashes completely through untouched
                    remaining_footer_size = size - (5 + 2)
                    f_dst.write(f_src.read(remaining_footer_size))
                # ====================================================================
                # CHUNKS PASS-THROUGH (ALL OTHER UNMODIFIED SECTIONS COPIED EXACTLY)
                # ====================================================================
                else:
                    f_src.seek(addr)
                    f_dst.write(f_src.read(12 + size))
                    print("\n[SUCCESS] Custom topology mesh exported cleanly with all global metadata synchronized.")
        return True
    except Exception as e:
        print(f"Critical adaptive serialization failure: {str(e)}")
        return False


class EXPORT_OT_anvil_mesh(bpy.types.Operator, ExportHelper):
    """Export active geometry layout to the AnvilSoft Mesh format"""
    bl_idname = "export_mesh.anvil_soft"
    bl_label = "Export AnvilSoft Mesh"
    bl_options = {'PRESET'}

    # Filter files showing only .mesh extensions in browser window panel
    #Output FIle Extension should be '*.Mesh' not '*.mesh'. Capital is important.
    filename_ext = ".Mesh"
    filter_glob: StringProperty(default="*.Mesh", options={'HIDDEN'})

    # User preference configuration window: requires the path to the original game asset
    source_template_path: StringProperty(
        name="Source Template (.Mesh)",
        description="Path to the original unmodded game mesh file to preserve file integrity headers",
        default= AnvilState.file_path,
        subtype='FILE_PATH'
    )

    def execute(self, context):
        # 1. Verify a valid template file was supplied
        if not self.source_template_path or not os.path.exists(self.source_template_path):
            self.report({'ERROR'}, "Source template path missing or invalid! Integrity cannot be verified.")
            return {'CANCELLED'}
            
        # 2. Verify active mesh selection
        active_obj = context.active_object
        if not active_obj or active_obj.type != 'MESH':
            self.report({'ERROR'}, "No active mesh object selected for export.")
            return {'CANCELLED'}

        # Execute our binary serialization pipeline manager
        success = perform_anvil_binary_injection(
            self.source_template_path, 
            self.filepath, 
            active_obj
        )
        
        if success:
            self.report({'INFO'}, f"Successfully exported: {os.path.basename(self.filepath)}")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "Export failed during binary payload generation.")
            return {'CANCELLED'}

# --- VIEWPORT FILE MENU REGISTRATION WRAPPERS ---
def menu_func_export(self, context):
    self.layout.operator(EXPORT_OT_anvil_mesh.bl_idname, text="AnvilSoft Mesh (.Mesh)")
    
def register_exporter_menu():
    # 1. Clean slate check: Unregister class first if it exists
    try:
        bpy.utils.unregister_class(EXPORT_OT_anvil_mesh)
    except Exception:
        pass
        
    # 2. ACCURATE PURGE MECHANISM: Look inside Blender's dynamic UI initialization cache
    # This fetches all registered extensions tracking the TOPBAR menu hooks.
    if hasattr(bpy.types.TOPBAR_MT_file_export, "_dyn_ui_initialize"):
        try:
            # Safely extract dynamic list instances matching your draw function name
            dyn_funcs = bpy.types.TOPBAR_MT_file_export._dyn_ui_initialize()
            for func in list(dyn_funcs):
                if hasattr(func, "__name__") and func.__name__ == "menu_func_export":
                    bpy.types.TOPBAR_MT_file_export.remove(func)
        except Exception:
            pass
    # Secondary flat lookup check if anything managed to slip through
    try:
        bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    except Exception:
        pass
    # 3. Freshly register the class and append EXACTLY ONE clean menu item
    bpy.utils.register_class(EXPORT_OT_anvil_mesh)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

def unregister_exporter_menu():
    try:
        bpy.utils.unregister_class(EXPORT_OT_anvil_mesh)
    except Exception:
        pass
        
    if hasattr(bpy.types.TOPBAR_MT_file_export, "_dyn_ui_initialize"):
        try:
            dyn_funcs = bpy.types.TOPBAR_MT_file_export._dyn_ui_initialize()
            for func in list(dyn_funcs):
                if hasattr(func, "__name__") and func.__name__ == "menu_func_export":
                    bpy.types.TOPBAR_MT_file_export.remove(func)
        except Exception:
            pass
            
# Register the Import and Export Menus as Add On
def register():
    register_importer_menu()
    register_exporter_menu()

# Allows executing the file browser natively if you hit "Run Script" from Text Editor
if __name__ == "__main__":
    register_importer_menu()
    register_exporter_menu()
    # Trigger the file pop-up dialog instantly on execution
    bpy.ops.import_mesh.anvil_soft('INVOKE_DEFAULT')
    #bpy.ops.export_mesh.anvil_soft('INVOKE_DEFAULT')

#---------Command to print Colors---------------------------
#print("First vertex color data:", obj.data.color_attributes["Physics_Panels"].data[5].color[:])



