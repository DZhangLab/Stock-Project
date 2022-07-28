package com.summer.stockproject.graph.entity;

import javax.persistence.Column;
import javax.persistence.Entity;
import javax.persistence.Id;
import javax.persistence.Table;

@Entity
@Table(name="company_names")
public class companyNames {
    @Id
    @Column(name="name")
    private String companyName;
    public companyNames() {
    }

    public companyNames(String companyName) {
        this.companyName = companyName;
    }

    public String getCompanyName() {
        return companyName;
    }

    public void setCompanyName(String companyName) {
        this.companyName = companyName;
    }

    @Override
    public String toString() {
        return "companyNames{" +
                "companyName='" + companyName + '\'' +
                '}';
    }
}
