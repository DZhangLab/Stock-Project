package com.summer.stockproject.entity;

import javax.persistence.Column;
import javax.persistence.Embeddable;
import javax.persistence.Id;
import java.io.Serializable;
import java.sql.Timestamp;
import java.util.Objects;

@Embeddable
public class mykey implements Serializable {
    @Column(name="company_name")
    private String companyName;

    @Column(name="time_point", columnDefinition ="DATETIME")
    private Timestamp timePoint;

    public mykey() {

    }

    public mykey(String companyName, Timestamp timePoint) {
        this.companyName = companyName;
        this.timePoint = timePoint;
    }

    public String getCompanyName() {
        return companyName;
    }

    public Timestamp getTimePoint() {
        return timePoint;
    }

    public void setCompanyName(String companyName) {
        this.companyName = companyName;
    }

    public void setTimePoint(Timestamp timePoint) {
        this.timePoint = timePoint;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        mykey mykey = (mykey) o;
        return Objects.equals(companyName, mykey.companyName) && Objects.equals(timePoint, mykey.timePoint);
    }

    @Override
    public int hashCode() {
        return Objects.hash(companyName, timePoint);
    }

    @Override
    public String toString() {
        return "mykey{" +
                "companyName='" + companyName + '\'' +
                ", timePoint=" + timePoint +
                '}';
    }
}