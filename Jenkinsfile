pipeline {
    agent any

    stages {

        // Run the build in the against the dev branch to check for compile errors
        stage('Build dev branch') {
            when {
                branch 'dev'
            }
            steps {
                echo 'Running dev_setup.sh...'
                sh 'CI=true /opt/mycroft/./dev_setup.sh --allow-root -sm'
            }
        }
    }
}
