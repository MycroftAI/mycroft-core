pipeline {
    agent any

    stages {

        // Run the build in the against the dev branch to check for compile errors
        stage('Build dev branch') {
            when {
                branch 'testing/docker-behave'
            }
            steps {
                echo 'Running Integration tests on ' + env.BRANCH_NAME
                sh ' echo ' + env.BRANCH_NAME
                sh ' docker run \
                    -v "$HOME/voigtmycroft:/root/.mycroft" \
                    --device /dev/snd \
                    -e BRANCH_NAME=' + env.BRANCH_NAME + ' \
                    -e PULSE_SERVER=unix:${XDG_RUNTIME_DIR}/pulse/native \
                    -v ${XDG_RUNTIME_DIR}/pulse/native:${XDG_RUNTIME_DIR}/pulse/native \
                    -v ~/.config/pulse/cookie:/root/.config/pulse/cookie \
                     mycroft-voigt-kampff:latest'
            }
        }
    }
}
