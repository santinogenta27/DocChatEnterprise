import re

# Leer app.py
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Encontrar el tab de Company Knowledge
start = content.find('# Tab 4.5.6: Company Knowledge')
end = content.find('# Tab 4.6: Chat Multi-Formato', start)

if start == -1 or end == -1:
    print("No se encontró el tab de Company Knowledge")
    exit(1)

tab_content = content[start:end]

# Reemplazar todas las referencias
accountability_tab = tab_content
accountability_tab = re.sub(r'# Tab 4\.5\.6: Company Knowledge', '# Tab 4.5.7: Accountability', accountability_tab)
accountability_tab = re.sub(r'Company Knowledge', 'Accountability', accountability_tab)
accountability_tab = re.sub(r'company_knowledge', 'accountability', accountability_tab)
accountability_tab = re.sub(r'CompanyKnowledge', 'Accountability', accountability_tab)
accountability_tab = re.sub(r'get_company_knowledge', 'get_accountability', accountability_tab)
accountability_tab = re.sub(r'run_company_knowledge', 'run_accountability', accountability_tab)
accountability_tab = re.sub(r'with gr\.Tab\("📚 Company Knowledge"\):', 'with gr.Tab("📋 Accountability"):', accountability_tab)
accountability_tab = re.sub(r'"📚 Company Knowledge"', '"📋 Accountability"', accountability_tab)
accountability_tab = re.sub(r'Company Knowledge -', 'Accountability -', accountability_tab)
accountability_tab = re.sub(r'- Company Knowledge', '- Accountability', accountability_tab)

# Guardar el resultado
with open('accountability_tab.txt', 'w', encoding='utf-8') as f:
    f.write(accountability_tab)

print(f"Tab clonado y adaptado: {len(accountability_tab)} caracteres")
print(f"Primeras líneas:\n{accountability_tab[:500]}")

