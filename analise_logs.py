import re
from collections import Counter
import sys

def parse_logs(log_file_path):
    print(f"Analisando o arquivo de logs: {log_file_path}")
    reasons = Counter()
    pattern = re.compile(r"REPORT_PERMISSION_DENIED.*?reason=([A-Z_]+)")

    try:
        with open(log_file_path, "r", encoding="utf-8") as f:
            for line in f:
                match = pattern.search(line)
                if match:
                    reasons[match.group(1)] += 1

        if not reasons:
            print("Nenhum registro de REPORT_PERMISSION_DENIED encontrado no log.")
            return

        print("\n=== Resultado da Análise ===")
        print(f"{'Motivo (Reason)':<30} | {'Quantidade':<10}")
        print("-" * 45)
        for reason, count in reasons.most_common():
            print(f"{reason:<30} | {count:<10}")

        print("\nCausa mais frequente:", reasons.most_common(1)[0][0])
    except FileNotFoundError:
        print("Arquivo de log não encontrado.")
    except Exception as e:
        print("Erro ao ler o arquivo de log:", e)

if __name__ == "__main__":
    log_path = "diagnostic_output.txt"
    if len(sys.argv) > 1:
        log_path = sys.argv[1]
    parse_logs(log_path)
