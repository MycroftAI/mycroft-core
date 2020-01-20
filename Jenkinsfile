pipeline {
    agent any

    stages {

        // Run the build in the against the dev branch to check for compile errors
        stage('Build dev branch') {
            when {
                branch 'testing/behave'
            }
            steps {
                echo 'Running dev_setup.sh... '
                sh 'CI=true ./dev_setup.sh --allow-root -sm'
            }
        }
    }
}
