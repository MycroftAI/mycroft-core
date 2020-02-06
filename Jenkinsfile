pipeline {
    agent any
    options {
        // Running builds concurrently could cause a race condition with
        // building the Docker image.
        disableConcurrentBuilds()
    }
    stages {
        // Run the build in the against the dev branch to check for compile errors
        stage('Run Integration Tests') {
            when {
                anyOf {
                    branch 'dev'
                    branch 'master'
                    changeRequest target: 'dev'
                }
            }
            steps {
                echo 'Building Test Docker Image'
                sh 'cp test/Dockerfile.test Dockerfile'
                sh 'docker build --target voigt_kampff -t mycroft-core:latest .'
                echo 'Running Tests'
                timeout(time: 10, unit: 'MINUTES')
                {
                    sh 'docker run \
                        -v "$HOME/voigtmycroft:/root/.mycroft" \
                        mycroft-core:latest'
                }
            }
        }
    }
    post {
        always('Important stuff') {
            echo 'Cleaning up docker containers and images'
            sh 'docker container prune --force'
            sh 'docker image prune --force'
        }
    }
}
