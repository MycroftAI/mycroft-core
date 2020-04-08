pipeline {
    agent any
    options {
        // Running builds concurrently could cause a race condition with
        // building the Docker image.
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '5'))
        lock resource: 'VoightKampff'
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
                    script: 'echo $BRANCH_NAME | sed -e "s#/#-#g"',
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
                            ssh root@157.245.127.234 "rm -rf /var/www/voight-kampff/core/${BRANCH_ALIAS}";
                            ssh root@157.245.127.234 "mv allure-report /var/www/voight-kampff/core/${BRANCH_ALIAS}"
                        '''
                    )
                    echo 'Report Published'
                }
                failure {
                    script {
                        // Create comment for Pull Requests
                        if (env.CHANGE_ID) {
                            echo 'Sending PR comment'
                            pullRequest.comment('Voight Kampff Integration Test Failed ([Results](https://reports.mycroft.ai/core/' + env.BRANCH_ALIAS + '))')
                        }
                    }
                    // Send failure email containing a link to the Jenkins build
                    // the results report and the console log messages to Mycroft
                    // developers, the developers of the pull request and the
                    // developers that caused the build to fail.
                    echo 'Sending Failure Email'
                    emailext (
                        attachLog: true,
                        subject: "FAILED - Core Integration Tests - Build ${BRANCH_NAME} #${BUILD_NUMBER}",
                        body: """
                            <p>
                                One or more integration tests failed. Use the
                                resources below to identify the issue and fix
                                the failing tests.
                            </p>
                            <br>
                            <p>
                                <a href='${BUILD_URL}'>
                                    Jenkins Build Details
                                </a>
                                &nbsp(Requires account on Mycroft's Jenkins instance)
                            </p>
                            <br>
                            <p>
                                <a href='https://reports.mycroft.ai/core/${BRANCH_ALIAS}'>
                                    Report of Test Results
                                </a>
                            </p>
                            <br>
                            <p>Console log is attached.</p>""",
                        replyTo: 'devops@mycroft.ai',
                        to: 'dev@mycroft.ai',
                        recipientProviders: [
                            [$class: 'RequesterRecipientProvider'],
                            [$class:'CulpritsRecipientProvider'],
                            [$class:'DevelopersRecipientProvider']
                        ]
                    )
                }
                success {
                    script {
                        if (env.CHANGE_ID) {
                            echo 'Sending PR comment'
                            pullRequest.comment('Voight Kampff Integration Test Succeeded  ([Results](https://reports.mycroft.ai/core/' + env.BRANCH_ALIAS + '))')
                        }
                    }
                    // Send success email containing a link to the Jenkins build
                    // and the results report to Mycroft developers, the developers
                    // of the pull request and the developers that caused the
                    // last failed build.
                    echo 'Sending Success Email'
                    emailext (
                        subject: "SUCCESS - Core Integration Tests - Build ${BRANCH_NAME} #${BUILD_NUMBER}",
                        body: """
                            <p>
                                All integration tests passed. No further action required.
                            </p>
                            <br>
                            <p>
                                <a href='${BUILD_URL}'>
                                    Jenkins Build Details
                                </a>
                                &nbsp(Requires account on Mycroft's Jenkins instance)
                            </p>
                            <br>
                            <p>
                                <a href='https://reports.mycroft.ai/core/${BRANCH_ALIAS}'>
                                    Report of Test Results
                                </a>
                            </p>""",
                        replyTo: 'devops@mycroft.ai',
                        to: 'dev@mycroft.ai',
                        recipientProviders: [
                            [$class: 'RequesterRecipientProvider'],
                            [$class:'CulpritsRecipientProvider'],
                            [$class:'DevelopersRecipientProvider']
                        ]
                    )
                }
            }
        }
        // Build a voight_kampff image for major releases.  This will be used
        // by the mycroft-skills repository to test skill changes.  Skills are
        // tested against major releases to determine if they play nicely with
        // the breaking changes included in said release.
        stage('Build Major Release Image') {
            when {
                tag "release/v*.*.0"
            }
            environment {
                // Tag name is usually formatted like "20.2.0" whereas skill
                // branch names are usually "20.02".  Reformat the tag name
                // to the skill branch format so this image will be easy to find
                // in the mycroft-skill repository.
                SKILL_BRANCH = sh(
                    script: 'echo $TAG_NAME | sed -e "s/v//g" -e "s/[.]0//g" -e "s/[.]/.0/g"',
                    returnStdout: true
                ).trim()
            }
            steps {
                echo 'Building ${TAG_NAME} Docker Image for Skill Testing'
                sh 'cp test/Dockerfile.test Dockerfile'
                sh 'docker build \
                    --target voight_kampff_builder \
                    --build-arg platform=mycroft_mark_1 \
                    -t voight-kampff-mark-1:${SKILL_BRANCH} .'
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
