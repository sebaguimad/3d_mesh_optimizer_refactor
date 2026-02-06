// geo/placa_hole_3d.geo
SetFactory("OpenCASCADE");

// =======================
// Parámetros
// =======================
Lx = 1.0;
Ly = 1.0;
t  = 0.01;      // espesor (1 cm)

R  = 0.15;      // radio del agujero
cx = 0.5;       // centro del agujero
cy = 0.5;

// =======================
// Placa base (2D)
// =======================
Rectangle(1) = {0, 0, 0, Lx, Ly};

// Agujero circular
Disk(2) = {cx, cy, 0, R, R};

// Placa con agujero
BooleanDifference{ Surface{1}; Delete; }{ Surface{2}; Delete; }

// =======================
// Extrusión 3D
// =======================
out[] = Extrude {0,0,t} {
  Surface{1};
  Layers{1};
};

// Dominio 3D
Physical Volume("DOM3D") = {out[1]};

// Punto de referencia (centro del agujero, mitad del espesor)
// NO es forzado: solo informativo
Point(1000) = {cx, cy, t/2};
Physical Point("REF") = {1000};