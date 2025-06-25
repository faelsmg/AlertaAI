from ultralytics import YOLO
import torch.serialization
import os
import shutil

# Adiciona permissão segura para carregar o modelo
from ultralytics.nn.tasks import DetectionModel
torch.serialization.add_safe_globals([DetectionModel])

# Carrega o modelo com segurança
modelo = YOLO("model/best.pt", task="detect")

def verificar_imagem(path_imagem):
    resultados = modelo(path_imagem, save=True, save_txt=False)

    pasta_saida = "runs/detect/predict"
    imagens = os.listdir(pasta_saida)
    imagens_processadas = [img for img in imagens if img.endswith(('.jpg', '.png'))]

    if imagens_processadas:
        ultima = imagens_processadas[-1]
        caminho_processado = os.path.join(pasta_saida, ultima)

        destino = os.path.join("static/uploads", ultima)
        shutil.copy(caminho_processado, destino)
        return True, destino

    return False, path_imagem
