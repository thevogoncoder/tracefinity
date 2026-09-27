# Exporting

## Bin export

From the bin editor, click **Export** to open the download menu. Available formats depend on what the bin contains.

### STL

Standard mesh format. Works with every slicer (PrusaSlicer, Cura, OrcaSlicer, etc.).

If the bin is too large for the configured bed size or the bin is separated by the partial bins configuration, the export menu shows **Full STL** (the merged file) and **ZIP** (split parts as separate STLs). The split count is shown in the sidebar banner.

### 3MF

Compressed format with multi-body support, generated for every bin. The file holds a single object whose parts are the bin (`bin`), any text labels (`labels`), and a print-in-place contrast insert (`insert`). Slicers load it as one multi-part object with every part where it was modelled, so you only need to assign a filament to each part. A loose contrast insert is not included; it stays a separate STL.

The 3MF always holds the whole bin. It is not split with oversized bins.

Internally uses trimesh for the 3MF scene assembly: each manifold becomes a named mesh under one parent node, which trimesh writes as one object built from components.

### Insert STL

Available when **Contrast Insert** is enabled in the bin configuration. This is a separate STL of just the insert piece, intended for printing in a contrasting colour. Download it from the export menu alongside the main bin STL.

With **Print in place** on, the insert STL is in the bin STL's coordinate frame and sits in the bottom of each pocket. The 3MF export already contains the insert as a part of the bin object. To use the STLs instead, import both files at once and load them as a single object with multiple parts so the slicer keeps their relative position, then assign the insert its own filament. The insert matches the unsplit bin STL only; it is not split with oversized bins.

## Tool export

From the tool editor, download the outline as an SVG file. Useful for laser cutting, CNC routing, or importing into CAD software.

## Print recommendations

Tracefinity bins are standard Gridfinity geometry, so the usual print settings apply:

| Setting | Recommendation |
|-|-|
| Layer height | 0.2mm default. 0.16mm for a smoother stacking lip. |
| Infill | 10-15%. Bin walls are thin and do not need much internal structure. |
| Supports | Not needed. Bins are designed to print without supports. |
| Material | PLA works well. PETG for more durability. |
| Orientation | Print with the base down (the default orientation in the exported file). |
