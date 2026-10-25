plugins {
    kotlin("jvm") version "2.1.21"
    application
}

repositories { mavenCentral() }

val fixtureVariant = providers.gradleProperty("fixtureVariant").orElse("reference").get()
require(fixtureVariant == "baseline" || fixtureVariant == "reference") {
    "fixtureVariant must be baseline or reference"
}

sourceSets {
    main {
        kotlin.srcDirs("shared", fixtureVariant)
    }
}

application { mainClass.set("lab.fixture.FixtureCheckKt") }
