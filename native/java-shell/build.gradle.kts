plugins {
    application
    java
}

group = "ai.louis"
version = "0.1.0"

java {
    toolchain {
        languageVersion.set(JavaLanguageVersion.of(21))
    }
}

repositories {
    mavenCentral()
}

dependencies {
    testImplementation(platform("org.junit:junit-bom:5.10.2"))
    testImplementation("org.junit.jupiter:junit-jupiter")
}

application {
    mainClass.set("ai.louis.shell.core.Bootstrap")
}

tasks.test {
    useJUnitPlatform()
}
