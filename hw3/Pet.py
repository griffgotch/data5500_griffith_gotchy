class Pet:
    species_lifespan = {
        "dog": 13,
        "cat": 15,
        "rabbit": 9
    }

    def __init__(self, name, age, species):
        self.name = name
        self.age = age
        self.species = species

    def age_in_human_years(self):
        if self.species == "dog":
            return self.age * 7
        elif self.species == "cat":
            return self.age * 6
        else:
            return self.age * 5

    def average_lifespan(self):
        return Pet.species_lifespan.get(self.species, "Unknown")

pet1 = Pet("Rollie", 10, "dog")
pet2 = Pet("Sophie", 4, "cat")
pet3 = Pet("Jojo", 2, "rabbit")

pets = [pet1, pet2, pet3]

for pet in pets:
    print(f"{pet.name} ({pet.species})")
    print(f"Age in human years: {pet.age_in_human_years()}")
    print(f"Average lifespan: {pet.average_lifespan()} years")
    print()