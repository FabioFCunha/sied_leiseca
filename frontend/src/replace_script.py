with open(r'd:\agenda_eventos_ols\frontend\src\pages\TechnicalReportsPage.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

import re

# 1. Replace materialsByTypeFromAgenda
old_func = '''function materialsByTypeFromAgenda(agenda) {
  const equipmentRemoved = [];
  const equipmentDistributed = [];
  const distributionRemoved = [];
  const distributionDistributed = [];

  const addEquipment = (name, quantity) => {
    if (name) {
      equipmentRemoved.push(`${name}${quantity ? ` - ${quantity}` : ""}`);
      equipmentDistributed.push(`${name} [   ]`);
    }
  };

  const addDistribution = (name, quantity) => {
    if (name) {
      distributionRemoved.push(`${name}${quantity ? ` - ${quantity}` : ""}`);
      distributionDistributed.push(`${name} [   ]`);
    }
  };

  for (let index = 1; index <= 7; index += 1) {
    addEquipment(agenda[`kit_${index}`], agenda[`kit_${index}_quantity`]);
    addDistribution(agenda[`material_${index}`], null);
  }

  if (agenda.materials?.length) {
    agenda.materials.forEach((item) => {
      addEquipment(item.dynamic_name, item.dynamic ? item.quantity : null);
      addDistribution(item.kit_name, item.kit ? item.quantity : null);
      addDistribution(item.material_name, item.material ? item.quantity : null);
    });
  }

  return {
    equipmentRemoved: equipmentRemoved.join("\\n"),
    equipmentDistributed: equipmentDistributed.join("\\n"),
    distributionRemoved: distributionRemoved.join("\\n"),
    distributionDistributed: distributionDistributed.join("\\n"),
  };
}'''

new_func = '''function extractMaterialCategories(agenda) {
  const dynamics = [];
  const supports = [];
  const kits = [];

  const add = (list, name) => {
    if (name && !list.includes(name)) list.push(name);
  };

  for (let index = 1; index <= 7; index += 1) {
    add(kits, agenda[`kit_${index}`]);
    add(supports, agenda[`material_${index}`]);
  }

  if (agenda.materials?.length) {
    agenda.materials.forEach((item) => {
      add(dynamics, item.dynamic_name);
      add(kits, item.kit_name);
      add(supports, item.material_name);
    });
  }

  return { dynamics, supports, kits };
}'''

content = content.replace(old_func, new_func)

# 2. Replace selectedMaterials
old_init = '''          const selectedMaterials = materialsByTypeFromAgenda(agenda);
          const formPayload = {
            ...current,
            materials_removed: current.materials_removed || materialsFromAgenda(agenda),
            materials_spent: current.materials_spent || "",
            actions: reportActions.map((action, idx) => {
              return {
                ...action,
                equipment_materials_removed: action.equipment_materials_removed || selectedMaterials.equipmentRemoved,
                equipment_materials_distributed: action.equipment_materials_distributed || selectedMaterials.equipmentDistributed,
                distribution_materials_removed: action.distribution_materials_removed || selectedMaterials.distributionRemoved,
                distribution_materials_distributed: action.distribution_materials_distributed || selectedMaterials.distributionDistributed,
              };
            }),
          };'''

new_init = '''          const selectedMaterials = extractMaterialCategories(agenda);
          const initialEquipment = [...selectedMaterials.dynamics, ...selectedMaterials.supports].join("\\n");
          const initialKits = selectedMaterials.kits.join("\\n");
          const formPayload = {
            ...current,
            materials_removed: current.materials_removed || materialsFromAgenda(agenda),
            materials_spent: current.materials_spent || "",
            actions: reportActions.map((action, idx) => {
              return {
                ...action,
                equipment_materials_removed: action.equipment_materials_removed || initialEquipment,
                equipment_materials_distributed: action.equipment_materials_distributed || initialEquipment,
                distribution_materials_removed: action.distribution_materials_removed || initialKits,
                distribution_materials_distributed: action.distribution_materials_distributed || initialKits,
              };
            }),
          };'''

content = content.replace(old_init, new_init)

# 3. Replace report-material-grid
old_grids = '''                <div className="report-material-grid">
                  <div className="field-label report-text-box">
                    <span>Dinâmica retirada</span>
                    <MaterialSummary value={action.equipment_materials_removed || ""} />
                  </div>
                  <div className="field-label report-text-box">
                    <span>Dinâmica distribuída</span>
                    <MaterialQuantityEditor value={action.equipment_materials_distributed || ""} onChange={(value) => updateAction(index, "equipment_materials_distributed", value)} />
                  </div>
                </div>
                <div className="report-material-grid" style={{ marginTop: '1rem' }}>
                  <div className="field-label report-text-box" style={{ gridColumn: '1 / -1' }}>
                    <span>Material distribuído</span>
                    <MaterialQuantityEditor value={action.distribution_materials_distributed || ""} onChange={(value) => updateAction(index, "distribution_materials_distributed", value)} />
                  </div>
                </div>'''

new_grids = '''                {(() => {
                  const cats = extractMaterialCategories(selectedAgenda);
                  const allEqRem = parseMaterialRows(action.equipment_materials_removed || "");
                  const allEqDist = parseMaterialRows(action.equipment_materials_distributed || "");
                  
                  const dynRem = serializeMaterialRows(allEqRem.filter(r => cats.dynamics.includes(r.name)));
                  const supRem = serializeMaterialRows(allEqRem.filter(r => cats.supports.includes(r.name)));
                  
                  const dynDist = serializeMaterialRows(allEqDist.filter(r => cats.dynamics.includes(r.name)));
                  const supDist = serializeMaterialRows(allEqDist.filter(r => cats.supports.includes(r.name)));

                  const handleDynDist = (val) => {
                    const combined = [val, supDist].filter(Boolean).join("\\n");
                    updateAction(index, "equipment_materials_distributed", combined);
                  };
                  const handleSupDist = (val) => {
                    const combined = [dynDist, val].filter(Boolean).join("\\n");
                    updateAction(index, "equipment_materials_distributed", combined);
                  };

                  return (
                    <>
                      {cats.dynamics.length > 0 && (
                      <div className="report-material-grid">
                        <div className="field-label report-text-box">
                          <span>Dinâmica retirada</span>
                          <MaterialSummary value={dynRem || cats.dynamics.join("\\n")} />
                        </div>
                        <div className="field-label report-text-box">
                          <span>Dinâmica distribuída</span>
                          <MaterialQuantityEditor value={dynDist || cats.dynamics.join("\\n")} onChange={handleDynDist} />
                        </div>
                      </div>
                      )}
                      {cats.supports.length > 0 && (
                      <div className="report-material-grid" style={{ marginTop: cats.dynamics.length > 0 ? '1rem' : 0 }}>
                        <div className="field-label report-text-box">
                          <span>Material de Apoio retirado</span>
                          <MaterialSummary value={supRem || cats.supports.join("\\n")} />
                        </div>
                        <div className="field-label report-text-box">
                          <span>Material de Apoio devolvido</span>
                          <MaterialQuantityEditor value={supDist || cats.supports.join("\\n")} onChange={handleSupDist} />
                        </div>
                      </div>
                      )}
                      <div className="report-material-grid" style={{ marginTop: '1rem' }}>
                        <div className="field-label report-text-box" style={{ gridColumn: '1 / -1' }}>
                          <span>Material distribuído</span>
                          <MaterialQuantityEditor value={action.distribution_materials_distributed || cats.kits.join("\\n")} onChange={(value) => updateAction(index, "distribution_materials_distributed", value)} />
                        </div>
                      </div>
                    </>
                  );
                })()}'''

content = content.replace(old_grids, new_grids)

with open(r'd:\agenda_eventos_ols\frontend\src\pages\TechnicalReportsPage.jsx', 'w', encoding='utf-8') as f:
    f.write(content)
print('Replaced:', 'extractMaterialCategories' in content)
