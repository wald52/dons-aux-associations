const fs = require('fs');
const path = require('path');
const d3 = require('d3-geo');

const geoDir = path.join(__dirname, '..', 'data', 'geo');
const svgDir = path.join(__dirname, '..', 'data', 'svg');

if (!fs.existsSync(svgDir)) {
    fs.mkdirSync(svgDir, { recursive: true });
}

// Mainland region codes (France métropolitaine)
const MAINLAND_REGION_CODES = ['11', '24', '27', '28', '32', '44', '52', '53', '75', '76', '84', '93', '94'];

// Overseas department/territory codes to exclude
const OVERSEAS_DEP_CODES = new Set(['971', '972', '973', '974', '975', '976', '977', '978', '984', '986', '987', '988', '989']);

function convertGeoJsonToSvg(geojsonFile, svgFile, width = 800, height = 600, idPrefix = 'region', filterType = null) {
    console.log(`Converting ${geojsonFile} to ${svgFile}...`);
    const geojson = JSON.parse(fs.readFileSync(path.join(geoDir, geojsonFile), 'utf-8'));
    
    let features = geojson.features;
    if (filterType === 'mainland-regions') {
        features = features.filter(f => MAINLAND_REGION_CODES.includes(f.properties.code));
        console.log(`  Filtered to ${features.length} mainland regions`);
    } else if (filterType === 'mainland-deps') {
        const before = features.length;
        features = features.filter(f => !OVERSEAS_DEP_CODES.has(f.properties.code));
        console.log(`  Filtered out overseas departments: ${before} -> ${features.length}`);
    }
    
    // Auto-fit projection to data bounds
    const projection = d3.geoMercator().fitSize([width, height], { type: 'FeatureCollection', features });
    const geoPath = d3.geoPath().projection(projection);

    // Generate SVG path data
    const svgPaths = features.map(feature => {
        const d = geoPath(feature.geometry);
        const code = feature.properties.code || feature.properties.CODE_DEPT || feature.properties.CODE_REG || '';
        const name = feature.properties.nom || feature.properties.LIBELLE || '';
        const id = idPrefix === 'dep' 
            ? (code === '2A' ? 'dep_2a' : code === '2B' ? 'dep_2b' : `dep_${code.padStart(2, '0')}`)
            : `${idPrefix}_${code}`;
        return `<path id="${id}" d="${d}" data-code="${code}" data-name="${name}" />`;
    }).join('\n');

    const svgContent = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}">
    <g fill="#8ad" stroke="#fff" stroke-width="0.5">
        ${svgPaths}
    </g>
</svg>`;

    fs.writeFileSync(path.join(svgDir, svgFile), svgContent, 'utf-8');
    console.log(`Generated ${svgFile}`);
}

// Convert files
convertGeoJsonToSvg('regions-2024.geojson', 'regions-2024.svg', 800, 600, 'reg', 'mainland-regions');
convertGeoJsonToSvg('departements-2024.geojson', 'departements-2024.svg', 800, 600, 'dep', 'mainland-deps');
convertGeoJsonToSvg('regions-2018.geojson', 'regions-2018.svg', 800, 600, 'reg', 'mainland-regions');
convertGeoJsonToSvg('departements-2018.geojson', 'departements-2018.svg', 800, 600, 'dep', 'mainland-deps');

console.log('Conversion complete.');
