import os
import subprocess
import sys

def correr_testes():
    pasta_testes = 'slitherlink-boards-public'
    
    ficheiros_txt = [f for f in os.listdir(pasta_testes) if f.endswith('.txt')]
    ficheiros_txt.sort()
    
    testes_passaram = 0
    testes_falharam = 0

    print("A iniciar os testes...\n" + "-"*40)

    for txt in ficheiros_txt:
        caminho_txt = os.path.join(pasta_testes, txt)
        caminho_out = os.path.join(pasta_testes, txt.replace('.txt', '.out'))
        
        if not os.path.exists(caminho_out):
            continue
            
        # Executa o programa
        with open(caminho_txt, 'r') as f_in:
            resultado = subprocess.run(
                [sys.executable, 'slitherlink.py'], 
                stdin=f_in, 
                capture_output=True, 
                text=True
            )
            
        # Lê a solução esperada
        with open(caminho_out, 'r') as f_out:
            esperado = f_out.read().strip()
            
        obtido = resultado.stdout.strip()
        erros = resultado.stderr.strip()
        
        # Faz .split() para comparar apenas as sequências de bits, ignorando Tabs ou Espaços
        esperado_bits = esperado.split()
        obtido_bits = obtido.split()
        
        if esperado_bits == obtido_bits and len(esperado_bits) > 0:
            print(f"✅ {txt}: PASSOU")
            testes_passaram += 1
        else:
            print(f"❌ {txt}: FALHOU")
            testes_falharam += 1
            
            # Análise do porquê de ter falhado:
            if erros:
                print("   -> ⚠️ O teu código gerou um ERRO:")
                # Imprime apenas as últimas 3 linhas do erro para não poluir muito
                print("\n".join(["      " + linha for linha in erros.split('\n')[-3:]]))
            elif not obtido:
                print("   -> 🕳️ O output devolvido foi completamente vazio (nenhuma solução encontrada).")
            else:
                print("   -> 🔢 Os números gerados não correspondem à solução exata.")
                print(f"      Esperado (início): {esperado_bits[:4]} ...")
                print(f"      Obtido   (início): {obtido_bits[:4]} ...")

    print("-" * 40)
    print(f"Resultado Final: {testes_passaram} Passaram | {testes_falharam} Falharam")

if __name__ == '__main__':
    correr_testes()