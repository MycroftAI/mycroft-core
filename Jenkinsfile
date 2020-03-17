pipeline {
    agent any
    options {
        // Running builds concurrently could cause a race condition with
        // building the Docker image.
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '5'))
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
            environment {
                // Some branches have a "/" in their name (e.g. feature/new-and-cool)
                // Some commands, such as those tha deal with directories, don't
                // play nice with this naming convention.  Define an alias for the
                // branch name that can be used in these scenarios.
                BRANCH_ALIAS = sh(
                    script: 'echo $BRANCH_NAME | sed -e "s#/#_#g"',
                    returnStdout: true
                ).trim()
            }
            steps {
                echo 'Building Mark I Voight-Kampff Docker Image'
                sh 'cp test/Dockerfile.test Dockerfile'
                sh 'docker build \
                    --target voight_kampff_builder \
                    --build-arg platform=mycroft_mark_1 \
                    -t voight-kampff-mark-1:${BRANCH_ALIAS} .'
                echo 'Running Mark I Voight-Kampff Test Suite'
                timeout(time: 60, unit: 'MINUTES')
                {
                    sh 'docker run \
                        -v "$HOME/voight-kampff/identity:/root/.mycroft/identity" \
                        -v "$HOME/voight-kampff/:/root/allure" \
                       voight-kampff-mark-1:${BRANCH_ALIAS} \
                        -f allure_behave.formatter:AllureFormatter \
                        -o /root/allure/allure-result --tags ~@xfail'
                }
            }
            post {
                always {
                    echo 'Report Test Results'
                    echo 'Changing ownership...'
                    sh 'docker run \
                        -v "$HOME/voight-kampff/:/root/allure" \
                        --entrypoint=/bin/bash \
                        voight-kampff-mark-1:${BRANCH_ALIAS} \
                        -x -c "chown $(id -u $USER):$(id -g $USER) \
                        -R /root/allure/"'

                    echo 'Transferring...'
                    sh 'rm -rf allure-result/*'
                    sh 'mv $HOME/voight-kampff/allure-result allure-result'
                    script {
                        allure([
                            includeProperties: false,
                            jdk: '',
                            properties: [],
                            reportBuildPolicy: 'ALWAYS',
                            results: [[path: 'allure-result']]
                        ])
                    }
                    unarchive mapping:['allure-report.zip': 'allure-report.zip']
                    sh (
                        label: 'Publish Report to Web Server',
                        script: '''scp allure-report.zip root@157.245.127.234:~;
                            ssh root@157.245.127.234 "unzip -o ~/allure-report.zip";
                            ssh root@157.245.127.234 "rm -rf /var/www/voight-kampff/${BRANCH_ALIAS}";
                            ssh root@157.245.127.234 "mv allure-report /var/www/voight-kampff/${BRANCH_ALIAS}"
                        '''
                    )
                    echo 'Report Published'
                }
            }
        }
    }
    post {
        cleanup {
            sh(
                label: 'Docker Container and Image Cleanup',
                script: '''
                    docker container prune --force;
                    docker image prune --force;
                '''
            )
        }
    }
}
