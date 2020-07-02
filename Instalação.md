# Mycroft

## Instalação

O método mais fácil de instalação do Mycroft é via git. 

Caso não tenha git instalado, abra o terminal e digite:
```sh
$ sudo apt install git
```

Para baixar o código, use a seguinte sequência de comandos:

```sh
$ cd ~/
$ git clone https://github.com/MycroftAI/mycroft-core.git
$ cd mycroft-core
$ bash dev_setup.sh
```

Primeiramente, sua pasta pessoal é acessada (home), então os arquivos do Mycroft são copiados para o diretório `mycroft-core`, em que o script de instalação é executado. Esse script configura dependências e um ambiente virtual. Se estiver executando em um ambiente diferente de Ubuntu, Debian, Arch ou Fedora, talvez precise instalar pacotes manualmente, seguindo os passos indicados pelo `dev_setup.sh`.

## Como rodar?

O Mycroft fornece o script `start-mycroft.sh` para controlar tarefas as comuns, como iniciar e reiniciar os serviços. Ele usa um ambiente virtual previamente criado.

Supondo que você instalou o `mycroft-core` em seu diretório home, execute:

```sh
$ cd ~/mycroft-core
$ ./start-mycroft.sh debug
```

O comando `debug` irá iniciar os serviços em segundo plano (microfone, etc), além de exibir uma CLI (Interface de Linha de Comando) a fim de permitir sua interação com o Mycroft e acompanhar o registro de logs.

Como alternativa, você pode executar `./start-mycroft.sh all` para iniciar os serviços **sem** a interface da linha de comandos. Posteriormente, você poderá acessar a CLI usando `./start-mycroft.sh cli`.

Os serviços em segundo plano podem ser parados como um grupo com:

```sh
$ ./stop-mycroft.sh
```

## Como usar?

O Mycroft AI, Inc. mantém um sistema de gerenciamento de dispositivos e contas conhecido como **Mycroft Home**. Os desenvolvedores podem se inscrever em: https://home.mycroft.ai

Por padrão, o mycroft-core está configurado para usar esse sistema. Ao dizer "Hey Mycroft, emparelhe meu dispositivo" ("Hey Mycroft, pair my device" - ou qualquer outra mensagem), você será informado de que seu dispositivo precisa ser emparelhado.

Então, o Mycroft falará um código de 6 dígitos que você precisará inserir na página de emparelhamento no site Mycroft Home. Uma vez configurado, sua unidade usará as chaves da API Mycroft para serviços como STT (serviço de transformação de Fala em Texto), previsão do tempo e várias outras funcionalidades. Se você não quiser usar o serviço Mycroft Home, poderá inserir suas próprias chaves de API nos arquivos de configuração.

## Funcionalidades (skills)

Mycroft não é nada sem funcionalidades (skills). Existem algumas funcionalidades que são baixadas automaticamente.


## Configurando sintetizador de voz em português

A fim de disponibilizar um sintetizador de voz (Text to Speech - TTS) em português para o Mycroft, é necessário instalar os pacotes `eSpeak` e `MBROLA`, que depende do eSpeak para funcionar.

```sh
$ sudo apt install espeak mbrola
```

Em sequência, para adicionar mais vozes em português:

```sh
$ sudo apt install mbrola-br*
```

## Mycroft em português


### Configurações de idioma

Podemos modificar o idioma do Mycroft utilizando o Configuration Manager.

1. Ative o ambiente virtual do Mycroft executando dentro da pasta `mycroft-core`:

```sh
source .venv/bin/activate
```

2. Atualize o `pip` e instale as dependências necessárias

```sh
pip install --upgrade pip
pip install mycroft-messagebus-client
```



```sh
mycroft-config set lang "pt-br"
```

Certifique-se de ter iniciado o Mycroft ao menos uma vez, bem como ter feito as configurações iniciais de emparelhamento.



---



### Via mycroft.conf

As informações avançadas do dispositivo Mycroft são salvas em um arquivo chamado `mycroft.conf`, formatado em JSON, que é salvo localmente. Contém informações sobre o próprio dispositivo. Seu dispositivo e suas funcionalidades instaladas utilizam esse arquivo para configurações.

**Onde estão armazenados os arquivos mycroft.conf?**
Em quatro locais possíveis:
- Padrão - `mycroft-core/mycroft/configuration/mycroft.conf`
- Remoto (de Home.Mycroft.ai) - `/var/tmp/mycroft_web_cache.json`
- Sistema - `/etc/mycroft/mycroft.conf`
- Usuário - `$HOME/.mycroft/mycroft.conf`

O Mycroft utiliza ordem de precedência: as configurações definidas no nível do usuário substituem as do nível do sistema. Se o arquivo não existir, o Mycroft passará para o nível seguinte.


Em `~/.mycroft/mycroft.conf`, adicione as seguintes configurações:

```js
{
  "lang": "pt-br",
  
  "tts": {
    "pulse_duck": false,
    "module": "espeak",
    "espeak": {
      "lang": "mb-br4",
      "voice": "mb-br4"
    }
  }
}
```

---


## Ligando repositórios a submódulos
 
 A fim de tornar o desenvolvimento mais organizado, é possível criar link entre respositórios. Assim, funcionalidades podem ser facilmente adicionadas, seguindo prática do repositorio oficial `mycroft-skills`.
 
```sh
$ git submodule add git@mygithost:skill-name skill-name
```

## Atualizando todos submódulos para última versão

Ao atualizar um submódulo, é necessário sincronizar o repositório de funcionalidades para corresponder à versal mais recente do mesmo. Para atualizar todos os módulos para a versão mais recente:

```sh
$ git pull --recurse-submodules
$ git submodule update --remote --recursive
```

---

## Mycroft Skills Manager

O MSM é uma ferramenta (linha de comando) utilizada para gerenciar, adicionar e remover funcionalidades em qualquer instalação do Mycroft. Ele pode instalar qualquer funcionalidade listada no Mycroft Skills Repository (ou qualquer outro disponibilizado pelo desenvolvedor). O msm é uma ferramenta útil para reconfigurar, instalar e desinstalar funcionalidades de maneira simplificada.

### Usando o MSM
O MSM foi reescrito no Python (anteriormente um bash). Primeiro você precisa entrar no ambiente virtual Mycroft (venv) com o seguinte comando, uma vez no diretório mycroft-core:

```sh
$ cd ~/mycroft-core
mycroft-core$ source .venv/bin/activate
```

Então, no terminal, será mostrado:
```sh
(.venv) rafaelbdefazio@rafaelbdefazio-dell:~/mycroft-core$ 
```
Caso esteja utilizando Picroft ou Mark 1:

```sh
mycroft-core$ source /opt/venvs/mycroft-core/bin/activate
```

Agora, poderá ter acesso ao Mycroft Skills Manager:

```sh
(.venv) rafaelbdefazio@rafaelbdefazio-dell:~/mycroft-core$  msm update
```

Para listagem dos comandos disponíveis, digite `msm -h`:

```sh
(.venv) root@rafaelbdefazio-dell:/home/rafaelbdefazio/mycroft-core# msm -h
usage: msm [-h]
           [-p {picroft,respeaker,mycroft_mark_1,default,mycroft_mark_2pi,kde,mycroft_mark_2}]
           [-u REPO_URL] [-b REPO_BRANCH] [-d SKILLS_DIR] [-c REPO_CACHE] [-l]
           [-r]
           {install,remove,search,info,list,update,default} ...

positional arguments:
  {install,remove,search,info,list,update,default}

optional arguments:
  -h, --help            show this help message and exit
  -p {picroft,respeaker,mycroft_mark_1,default,mycroft_mark_2pi,kde,mycroft_mark_2}, --platform {picroft,respeaker,mycroft_mark_1,default,mycroft_mark_2pi,kde,mycroft_mark_2}
  -u REPO_URL, --repo-url REPO_URL
  -b REPO_BRANCH, --repo-branch REPO_BRANCH
  -d SKILLS_DIR, --skills-dir SKILLS_DIR
  -c REPO_CACHE, --repo-cache REPO_CACHE
  -l, --latest          Disable skill versioning
  -r, --raw

```

---

# Customização de pasta de skills

No arquivo `dev_setup.sh`, linhas `258-272`, a criação das pastas de skills é feita, bem como a criação do link entre `~/mycroft-core/skills` e `/opt/mycroft//skills`:

```sh

echo 'The standard location for Mycroft skills is under /opt/mycroft/skills.'
    if [[ ! -d /opt/mycroft/skills ]] ; then
        echo 'This script will create that folder for you.  This requires sudo'
        echo 'permission and might ask you for a password...'
        setup_user=$USER
        setup_group=$(id -gn $USER)
        $SUDO mkdir -p /opt/mycroft/skills
        $SUDO chown -R ${setup_user}:${setup_group} /opt/mycroft
        echo 'Created!'
    fi
    if [[ ! -d skills ]] ; then
        ln -s /opt/mycroft/skills skills
        echo "For convenience, a soft link has been created called 'skills' which leads"
        echo 'to /opt/mycroft/skills.'
    fi
```
    
O diretório `/opt/mycroft/` tem as seguintes permissões:

```sh
$ getfacl opt/mycroft/
# file: opt/mycroft/
# owner: <usuario>
# group: <usuario>
user::rwx
group::r-x
other::r-x
```

Para alterar para `/opt/AVA`:

```sh

echo 'The standard location for Mycroft skills is under /opt/AVA/skills.'
    if [[ ! -d /opt/AVA/skills ]] ; then
        echo 'This script will create that folder for you.  This requires sudo'
        echo 'permission and might ask you for a password...'
        setup_user=$USER
        setup_group=$(id -gn $USER)
        $SUDO mkdir -p /opt/AVA/skills
        $SUDO chown -R ${setup_user}:${setup_group} /opt/AVA
        echo 'Created!'
    fi
    if [[ ! -d skills ]] ; then
        ln -s /opt/AVA/skills skills
        echo "For convenience, a soft link has been created called 'skills' which leads"
        echo 'to /opt/AVA/skills.'
    fi
```

Output:

```sh
The standard location for Mycroft skills is under /opt/AVA/skills.
This script will create that folder for you.  This requires sudo
permission and might ask you for a password...
Created!
```


### Atualizando mycroft.conf

Atualizar configurçaão `"data_dir": "/opt/mycroft"` para `"data_dir": "/opt/AVA"` em `mycroft.conf`.

Também é necessário modificar em o arquivo `~/mycroft-core/scripts/prepare-msm.sh` (linha 17):

```mycroft_root_dir="/opt/mycroft"``` para 
```mycroft_root_dir="/opt/AVA"``` 

Assim que iniciar o Mycroft, as configurações serão aplicadas:

```sh
Initializing...
Changing ownership of /opt/AVA to user: <usuario> with group: <usuario>
alterado o dono de '/opt/AVA/skills' de root:root para <usuario>:<usuario>
alterado o dono de '/opt/AVA' de root:root para <usuario>:<usuario>
Starting background service bus
```
### Modificando ~/.mycroft

Para modificar o diretório de usuário, em `mycroft.conf`:

```sh  "skills": {
    "directory": "~/.ava/skills"
    }
 ```
