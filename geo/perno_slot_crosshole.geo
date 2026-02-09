SetFactory("OpenCASCADE");

// ========= Parámetros (mm) =========
L          = 80;
D_shank    = 12;
D_head     = 20;
H_head     = 10;

D_neck     = 9;
L_neck     = 20;

d_cross    = 3;    // taladro transversal
w_slot     = 2.5;  // ranura longitudinal
depth_slot = 1.2;

lcMin = 0.6;
lcMax = 3.0;

// ========= Sólido base =========
R_shank = D_shank/2;
R_head  = D_head/2;
R_neck  = D_neck/2;

// Vástago
v_shank = newv;
Cylinder(v_shank) = {0,0,0, 0,0,L, R_shank};

// Cabeza
v_head = newv;
Cylinder(v_head) = {0,0,L, 0,0,H_head, R_head};

// Cuello (cilindro a sustraer)
v_neck_tool = newv;
Cylinder(v_neck_tool) = {0,0,L-L_neck, 0,0,L_neck, R_neck};

// Generar cuello por diferencia
v_shank2[] = BooleanDifference{ Volume{v_shank}; Delete; }{ Volume{v_neck_tool}; Delete; };

// Unir con cabeza
v_base[] = BooleanUnion{ Volume{v_shank2[]}; Delete; }{ Volume{v_head}; Delete; };

// ========= Ranura longitudinal =========
v_slot = newv;
Box(v_slot) = {-w_slot/2, R_shank - depth_slot, 0, w_slot, depth_slot*2, L};

// ========= Taladro transversal =========
v_hole = newv;
Cylinder(v_hole) = {0,0,L-L_neck/2, 1,0,0, d_cross/2};

// ========= Cortes =========
v_final[] = BooleanDifference{ Volume{v_base[]}; Delete; }{ Volume{v_slot, v_hole}; Delete; };

// ========= Malla =========
Mesh.CharacteristicLengthMin = lcMin;
Mesh.CharacteristicLengthMax = lcMax;

// Para que el volumen quede “marcado”
Physical Volume("SOLID") = { v_final[] };
